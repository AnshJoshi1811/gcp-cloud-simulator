"""
Reconciles moto's in-memory AWS state against Docker reality.

This is MiniCloud's actual differentiator from a plain AWS mock: every
`running` EC2 instance known to moto gets a real Docker container; every VPC
gets a real Docker network; terminated instances get their container removed.
Runs as a background thread, polling every POLL_INTERVAL_SECONDS, so it
naturally satisfies "reconcile state with Docker reality on startup" too —
the first poll after boot is the same diff as every other poll.
"""

import base64
import logging
import threading
import time
from typing import Dict, Optional

from . import docker_manager
from . import state_db

logger = logging.getLogger("minicloud.reconciler")

POLL_INTERVAL_SECONDS = 2
DEFAULT_ACCOUNT_ID = "123456789012"

# AMI id (substring match, checked in order) -> Docker image.
AMI_IMAGE_MAP = [
    ("ubuntu", "ubuntu:22.04"),
    ("alpine", "alpine:3.19"),
    ("nginx", "nginx:alpine"),
]
DEFAULT_IMAGE = "alpine:3.19"

# instance_type -> (cpu_count, mem_limit_mb). Unknown types fall back to the
# smallest tier, matching a real cloud's conservative default.
INSTANCE_TYPE_LIMITS = {
    "t2.nano": (1, 256),
    "t2.micro": (1, 512),
    "t2.small": (1, 1024),
    "t2.medium": (2, 2048),
    "t3.micro": (1, 512),
    "t3.small": (1, 1024),
    "t3.medium": (2, 2048),
    "m5.large": (2, 4096),
}


def _image_for_ami(ami_id: str) -> str:
    ami_lower = (ami_id or "").lower()
    for needle, image in AMI_IMAGE_MAP:
        if needle in ami_lower:
            return image
    return DEFAULT_IMAGE


def _limits_for_instance_type(instance_type: str):
    return INSTANCE_TYPE_LIMITS.get(instance_type, (1, 512))


def _decode_user_data(user_data) -> Optional[str]:
    if not user_data:
        return None
    # moto represents EC2 user_data as a Base64EncodedString object (not a
    # plain str) with its own .decode(); plain strings fall through to the
    # manual base64 decode below.
    if hasattr(user_data, "decode") and not isinstance(user_data, (str, bytes)):
        try:
            return user_data.decode("utf-8")
        except Exception:
            pass
    try:
        return base64.b64decode(user_data).decode("utf-8", errors="replace")
    except Exception:
        return str(user_data)


def _published_ports_for_security_groups(instance) -> Dict[int, int]:
    """Translate each attached security group's TCP ingress rules into
    container port publishes (host port auto-assigned by Docker)."""
    ports: Dict[int, int] = {}
    for group in instance.security_groups or []:
        for rule in getattr(group, "ingress_rules", []):
            if rule.ip_protocol not in ("tcp", "-1"):
                continue
            from_port = rule.from_port or 0
            to_port = rule.to_port or from_port
            for port in range(from_port, min(to_port, from_port + 10) + 1):
                ports[port] = 0  # 0 -> Docker auto-assigns a free host port
    return ports


class Reconciler:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Reconciler started")

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.reconcile_once()
            except Exception:
                logger.exception("Reconciliation pass failed")
            time.sleep(POLL_INTERVAL_SECONDS)

    def reconcile_once(self):
        try:
            from moto.ec2.models import ec2_backends
        except Exception:
            return

        account_backends = ec2_backends.get(DEFAULT_ACCOUNT_ID)
        if not account_backends:
            return

        for region, backend in account_backends.items():
            self._reconcile_vpcs(backend)
            self._reconcile_instances(backend)

    def _reconcile_vpcs(self, backend):
        for vpc_id, vpc in getattr(backend, "vpcs", {}).items():
            network_name = f"minicloud-vpc-{vpc_id}"
            existing = state_db.get_resource(vpc_id)
            if existing:
                continue
            try:
                network_id = docker_manager.ensure_network(network_name, getattr(vpc, "cidr_block", None))
                state_db.upsert_resource(vpc_id, "vpc", docker_id=network_id, docker_name=network_name)
                logger.info(f"Reconciled VPC {vpc_id} -> Docker network {network_name}")
            except Exception:
                # One VPC failing to map to a Docker network must not block
                # every other VPC or any EC2 instance from reconciling.
                logger.exception(f"Failed to reconcile VPC {vpc_id}, will retry next pass")

    def _reconcile_instances(self, backend):
        live_instance_ids = set()
        for reservation in backend.reservations.values():
            for instance in reservation.instances:
                live_instance_ids.add(instance.id)
                try:
                    self._reconcile_one_instance(instance)
                except Exception:
                    logger.exception(f"Failed to reconcile instance {instance.id}, will retry next pass")

        # Containers for instances moto no longer tracks at all (shouldn't
        # normally happen — terminated instances stay in reservations with
        # state=terminated — but handles state resets cleanly).
        for res in state_db.list_resources("ec2_instance"):
            if res["resource_id"] not in live_instance_ids:
                docker_manager.remove_container(res["docker_id"])
                state_db.delete_resource(res["resource_id"])

    def _reconcile_one_instance(self, instance):
        existing = state_db.get_resource(instance.id)
        state = instance.state
        last_synced_state = (existing or {}).get("extra", "").split(";")[0].replace("state=", "")

        if state in ("running", "pending"):
            if not existing or not existing["docker_id"]:
                self._provision_instance(instance)
            elif last_synced_state == "stopped":
                docker_manager.start_container(existing["docker_id"])
                state_db.upsert_resource(
                    instance.id, "ec2_instance", docker_id=existing["docker_id"],
                    docker_name=existing["docker_name"], extra=f"state=running",
                )

        elif state == "stopped":
            if existing and existing["docker_id"] and last_synced_state != "stopped":
                docker_manager.stop_container(existing["docker_id"])
                state_db.upsert_resource(
                    instance.id, "ec2_instance", docker_id=existing["docker_id"],
                    docker_name=existing["docker_name"], extra="state=stopped",
                )

        elif state == "terminated":
            if existing and existing["docker_id"]:
                docker_manager.remove_container(existing["docker_id"])
                state_db.delete_resource(instance.id)

    def _provision_instance(self, instance):
        vpc_id = getattr(instance, "vpc_id", None)
        network_name = f"minicloud-vpc-{vpc_id}" if vpc_id else "bridge"
        image = _image_for_ami(instance.image_id)
        cpu_count, mem_limit_mb = _limits_for_instance_type(instance.instance_type)
        user_data = _decode_user_data(getattr(instance, "user_data", None))
        ports = _published_ports_for_security_groups(instance)
        container_name = f"minicloud-ec2-{instance.id}"

        result = docker_manager.run_instance_container(
            name=container_name,
            image=image,
            network=network_name,
            cpu_count=cpu_count,
            mem_limit_mb=mem_limit_mb,
            user_data=user_data,
            published_ports=ports,
            labels={docker_manager.LABEL_RESOURCE_ID: instance.id},
        )
        state_db.upsert_resource(
            instance.id, "ec2_instance", docker_id=result["container_id"], docker_name=container_name,
            extra=f"state=running;image={image}",
        )
        # Mirror the assigned container IP back onto the moto instance so
        # DescribeInstances reflects where the container actually lives.
        if result.get("internal_ip"):
            instance.private_ip_address = result["internal_ip"]
        logger.info(f"Provisioned EC2 instance {instance.id} -> container {container_name} ({image})")


reconciler = Reconciler()
