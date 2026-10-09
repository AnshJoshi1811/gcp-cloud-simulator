"""Docker operations for MiniCloud. Falls back to stub mode if Docker is
unavailable, mirroring the pattern already used by this repo's GCP emulator
(backend/app/core/docker_manager.py) so the server stays alive and the AWS
API / Terraform cycle keeps working even without a Docker daemon."""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger("minicloud.docker")

try:
    import docker
    client = docker.from_env()
    client.ping()
    DOCKER_AVAILABLE = True
except Exception as e:
    docker = None
    client = None
    DOCKER_AVAILABLE = False
    logger.warning(f"Docker unavailable, running in stub mode: {e}")

LABEL_MANAGED = "minicloud"
LABEL_RESOURCE_TYPE = "minicloud.resource"
LABEL_RESOURCE_ID = "minicloud.id"


def ensure_network(name: str, cidr: Optional[str] = None) -> str:
    """Create (or reuse) a Docker bridge network. Returns its id (or a stub id)."""
    if not DOCKER_AVAILABLE:
        return f"stub-net-{name}"
    try:
        net = client.networks.get(name)
        return net.id
    except docker.errors.NotFound:
        pass
    ipam = None
    if cidr:
        ipam = docker.types.IPAMConfig(pool_configs=[docker.types.IPAMPool(subnet=cidr)])
    net = client.networks.create(
        name, driver="bridge", ipam=ipam, labels={LABEL_MANAGED: "true", LABEL_RESOURCE_TYPE: "vpc"}
    )
    return net.id


def delete_network(name: str) -> None:
    if not DOCKER_AVAILABLE:
        return
    try:
        net = client.networks.get(name)
        net.remove()
    except Exception:
        pass


def run_instance_container(
    name: str,
    image: str,
    network: str,
    cpu_count: Optional[int] = None,
    mem_limit_mb: Optional[int] = None,
    user_data: Optional[str] = None,
    published_ports: Optional[Dict[int, int]] = None,
    labels: Optional[Dict[str, str]] = None,
) -> Dict[str, Optional[str]]:
    """Run a container representing an EC2 instance.

    Returns {"container_id", "internal_ip"}.
    """
    if not DOCKER_AVAILABLE:
        logger.info(f"[stub] would run container {name} from image {image}")
        return {"container_id": f"stub-{name}", "internal_ip": "10.0.0.1"}

    try:
        existing = client.containers.get(name)
        existing.remove(force=True)
    except docker.errors.NotFound:
        pass

    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        try:
            client.images.pull(image)
        except Exception as e:
            logger.error(f"Failed to pull image {image}: {e}")

    command = "sleep infinity"
    if user_data:
        # Run the user's startup script, then keep the container alive so it
        # keeps representing a "running instance" the way a real EC2 host would.
        escaped = user_data.replace("'", "'\\''")
        command = f"sh -c '{escaped} ; sleep infinity'"

    all_labels = {LABEL_MANAGED: "true", LABEL_RESOURCE_TYPE: "ec2_instance", **(labels or {})}

    kwargs = dict(
        name=name,
        command=command,
        detach=True,
        network=network,
        labels=all_labels,
        mem_limit=f"{mem_limit_mb}m" if mem_limit_mb else None,
        nano_cpus=int(cpu_count * 1e9) if cpu_count else None,
    )
    if published_ports:
        kwargs["ports"] = {f"{container_port}/tcp": host_port for container_port, host_port in published_ports.items()}

    container = client.containers.run(image, **kwargs)
    container.reload()
    internal_ip = container.attrs.get("NetworkSettings", {}).get("Networks", {}).get(network, {}).get("IPAddress")
    return {"container_id": container.id, "internal_ip": internal_ip}


def stop_container(container_id: str) -> None:
    if not DOCKER_AVAILABLE or container_id.startswith("stub-"):
        return
    try:
        client.containers.get(container_id).stop()
    except Exception:
        pass


def start_container(container_id: str) -> None:
    if not DOCKER_AVAILABLE or container_id.startswith("stub-"):
        return
    try:
        client.containers.get(container_id).start()
    except Exception:
        pass


def remove_container(container_id: str) -> None:
    if not DOCKER_AVAILABLE or container_id.startswith("stub-"):
        return
    try:
        client.containers.get(container_id).remove(force=True)
    except Exception:
        pass


def container_logs(container_id: str, tail: int = 200) -> str:
    if not DOCKER_AVAILABLE or container_id.startswith("stub-"):
        return "(stub mode — no real container, no logs)"
    try:
        return client.containers.get(container_id).logs(tail=tail).decode(errors="replace")
    except Exception as e:
        return f"(failed to read logs: {e})"


def list_managed_containers() -> List[Dict[str, str]]:
    if not DOCKER_AVAILABLE:
        return []
    containers = client.containers.list(all=True, filters={"label": f"{LABEL_MANAGED}=true"})
    return [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "resource_type": c.labels.get(LABEL_RESOURCE_TYPE, ""),
            "resource_id": c.labels.get(LABEL_RESOURCE_ID, ""),
        }
        for c in containers
    ]


def list_managed_networks() -> List[Dict[str, str]]:
    if not DOCKER_AVAILABLE:
        return []
    networks = client.networks.list(filters={"label": f"{LABEL_MANAGED}=true"})
    return [{"id": n.id, "name": n.name} for n in networks]


def destroy_all_managed_resources() -> Dict[str, int]:
    """Remove every MiniCloud-managed container and network. Used by
    `minicloud destroy-all`; works from Docker labels alone, so it's safe
    even if MiniCloud's own state DB or Terraform state was lost."""
    removed = {"containers": 0, "networks": 0}
    if not DOCKER_AVAILABLE:
        return removed
    for c in client.containers.list(all=True, filters={"label": f"{LABEL_MANAGED}=true"}):
        try:
            c.remove(force=True)
            removed["containers"] += 1
        except Exception:
            pass
    for n in client.networks.list(filters={"label": f"{LABEL_MANAGED}=true"}):
        try:
            n.remove()
            removed["networks"] += 1
        except Exception:
            pass
    return removed
