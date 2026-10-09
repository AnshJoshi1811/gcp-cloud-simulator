"""Docker Manager - Container operations (falls back to no-op stubs if Docker is unavailable)"""
import docker
import ipaddress
import time
import random
from typing import Optional, Dict, List

try:
    client = docker.from_env()
    _docker_available = True
except Exception as e:
    # Keep API alive even if Docker socket is not reachable (e.g., sandbox/permission issues)
    client = None
    _docker_available = False
    print(f"⚠️  Docker unavailable, running in stub mode: {e}")

# simple IP generator for stub mode
_stub_ip_counter = 10
def _stub_ip(base: str = "10.250.0.") -> str:
    global _stub_ip_counter
    _stub_ip_counter += 1
    return f"{base}{_stub_ip_counter}"

def create_docker_network_with_cidr(name: str, cidr: str, project: str) -> str:
    """Create Docker network with custom CIDR range
    
    Args:
        name: Network name
        cidr: CIDR range (e.g., '10.99.0.0/16')
        project: GCP project ID
        
    Returns:
        Docker network ID
    """
    docker_network_name = f"gcp-vpc-{project}-{name}"

    if not _docker_available:
        print(f"ℹ️  Stub network {docker_network_name} (cidr {cidr}) created without Docker")
        return docker_network_name
    
    try:
        # Check if already exists
        existing = client.networks.get(docker_network_name)
        print(f"✓ Network {docker_network_name} already exists")
        return existing.id
    except docker.errors.NotFound:
        pass
    
    # Parse CIDR to get gateway
    network_obj = ipaddress.ip_network(cidr, strict=False)
    gateway = str(list(network_obj.hosts())[0])
    
    # Create IPAM configuration
    ipam_pool = docker.types.IPAMPool(
        subnet=cidr,
        gateway=gateway
    )
    ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
    
    # Create network
    try:
        network = client.networks.create(
            docker_network_name,
            driver="bridge",
            ipam=ipam_config,
            labels={
                "gcp-project": project,
                "gcp-network": name,
                "gcp-cidr": cidr
            }
        )
    except docker.errors.APIError as e:
        raise RuntimeError(f"Docker network create error: {e}")
    
    print(f"✓ Created Docker network {docker_network_name} with CIDR {cidr}, gateway {gateway}")
    return network.id

def create_default_network():
    """Create default GCP Docker network with IPAM configuration"""
    if not _docker_available:
        print("ℹ️  Stub default network gcp-default ready (Docker unavailable)")
        class _StubNet:
            name = "gcp-default"
            id = "stub-net"
            attrs = {"IPAM": {"Config": [{"Subnet": "10.128.0.0/20"}]}}
        return _StubNet()
    try:
        return client.networks.get("gcp-default")
    except docker.errors.NotFound:
        print("Creating gcp-default Docker network with IPAM...")
        
        # Create IPAM configuration for default network
        ipam_pool = docker.types.IPAMPool(
            subnet='10.128.0.0/20',
            gateway='10.128.0.1'
        )
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        
        return client.networks.create(
            "gcp-default", 
            driver="bridge",
            ipam=ipam_config
        )


def ip_in_docker_network(network_name: str, ip_address: str) -> bool:
    """Return True if the IPv4 address belongs to any IPAM pool of the Docker network."""
    if not _docker_available:
        return True
    try:
        net = client.networks.get(network_name)
    except Exception:
        # If network can't be found, default network contains 10.128.0.0/20
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip in ipaddress.ip_network("10.128.0.0/20")
        except Exception:
            return False

    configs = net.attrs.get("IPAM", {}).get("Config", []) or []
    try:
        ip = ipaddress.ip_address(ip_address)
    except Exception:
        return False

    for c in configs:
        sub = c.get("Subnet") or c.get("subnet")
        if not sub:
            continue
        try:
            if ip in ipaddress.ip_network(sub):
                return True
        except Exception:
            continue
    return False

def create_container(name: str, network: str = "gcp-default", image: str = "ubuntu:22.04", ip_address: Optional[str] = None):
    """
    Create Docker container for VM instance with optional static IP assignment
    
    Args:
        name: VM instance name
        network: Docker network name
        image: Container image
        ip_address: Optional static IP to assign (e.g., "10.128.0.2")
    
    Returns: {"container_id": str, "container_name": str, "internal_ip": str}
    """
    container_name = f"gcp-vm-{name}"

    if not _docker_available:
        # Stub: just return fake ids and IPs
        internal_ip = ip_address or _stub_ip()
        return {"container_id": f"stub-{container_name}", "container_name": container_name, "internal_ip": internal_ip}

    # Prevent accidental reuse of an existing container name
    try:
        existing = client.containers.get(container_name)
        raise RuntimeError(f"Container name '{container_name}' already in use (id={existing.id[:12]})")
    except docker.errors.NotFound:
        pass
    
    # Ensure network exists
    try:
        net = client.networks.get(network)
    except Exception:
        net = create_default_network()
    
    # Create container WITHOUT attaching to network yet (if we need specific IP)
    if ip_address:
        # Validate requested IP is inside the Docker network's IPAM pools
        if not ip_in_docker_network(net.name, ip_address):
            configs = net.attrs.get("IPAM", {}).get("Config", []) or []
            pools = [c.get("Subnet") or c.get("subnet") for c in configs if c.get("Subnet") or c.get("subnet")]
            raise RuntimeError(f"Requested IP {ip_address} is not contained in Docker network '{net.name}' subnets: {pools}")
        container = client.containers.run(
            image,
            name=container_name,
            command="sleep infinity",
            detach=True,
            network=None,  # Don't attach yet
            hostname=name
        )
        
        # Connect to network with specific IP
        try:
            net.connect(container, ipv4_address=ip_address)
        except docker.errors.APIError as e:
            # Clean up the created container if connect fails
            try:
                container.remove(force=True)
            except Exception:
                pass
            raise RuntimeError(f"Failed to connect container to network: {e}")
        print(f"✓ Assigned IP {ip_address} to container {container_name}")
        
        container.reload()
        final_ip = ip_address
    else:
        # Create with auto-assigned IP
        try:
            container = client.containers.run(
                image,
                name=container_name,
                command="sleep infinity",
                detach=True,
                network=network,
                hostname=name
            )
        except docker.errors.APIError as e:
            raise RuntimeError(f"Failed to create container with auto-assigned IP: {e}")
        
        # Get auto-assigned IP
        container.reload()
        final_ip = container.attrs['NetworkSettings']['Networks'][network]['IPAddress']
        print(f"✓ Auto-assigned IP {final_ip} to container {container_name}")
    
    return {
        "container_id": container.id,
        "container_name": container_name,
        "internal_ip": final_ip
    }

def stop_container(container_id: str):
    """Stop Docker container"""
    if not _docker_available:
        return True
    try:
        container = client.containers.get(container_id)
        container.stop()
        return True
    except Exception as e:
        print(f"Error stopping container: {e}")
        return False

def start_container(container_id: str):
    """Start Docker container"""
    if not _docker_available:
        return True
    try:
        container = client.containers.get(container_id)
        container.start()
        return True
    except Exception as e:
        print(f"Error starting container: {e}")
        return False

def delete_container(container_id: str):
    """Delete Docker container"""
    if not _docker_available:
        return True
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
        return True
    except Exception as e:
        print(f"Error deleting container: {e}")
        return False

def get_container_status(container_id: str) -> Optional[str]:
    """Get container status"""
    if not _docker_available:
        return "running"
    try:
        container = client.containers.get(container_id)
        return container.status
    except:
        return None


# ─── GKE / k3s helpers ────────────────────────────────────────────────────────

# Pinned k3s images per GKE-compatible Kubernetes version
K3S_VERSION_MAP: dict[str, str] = {
    "1.27": "rancher/k3s:v1.27.13-k3s1",
    "1.28": "rancher/k3s:v1.28.9-k3s1",
    "1.29": "rancher/k3s:v1.29.4-k3s1",
    "1.30": "rancher/k3s:v1.30.0-k3s1",
}

_GKE_NETWORK = "gcs-stimulator-gke"   # dedicated Docker bridge for all GKE clusters
_USED_PORTS: set[int] = set()
_PORT_RANGE = range(6443, 6503)        # 60 slots → 60 simultaneous clusters


def _ensure_gke_network() -> None:
    """Create the dedicated GKE Docker bridge network if it doesn't exist."""
    if not _docker_available:
        return
    try:
        client.networks.get(_GKE_NETWORK)
    except docker.errors.NotFound:
        client.networks.create(
            _GKE_NETWORK,
            driver="bridge",
            labels={"gcs-stimulator": "true", "service": "gke"},
        )
        print(f"✓ Created Docker network {_GKE_NETWORK}")


def _find_free_port() -> int:
    """Find an unused host port in the GKE reserved range 6443-6502."""
    if not _docker_available:
        return random.choice(list(_PORT_RANGE))
    import socket
    for port in _PORT_RANGE:
        if port in _USED_PORTS:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                _USED_PORTS.add(port)
                return port
            except OSError:
                continue
    raise RuntimeError("No free port available in GKE range 6443-6502")


def create_k3s_cluster(cluster_name: str, kubernetes_version: str = "1.28") -> dict:
    """Spin up a k3s container as a GKE cluster control plane.

    Uses a dedicated Docker network, a named volume for persistence, host-port
    mapping for multi-cluster support, and proper TLS SANs so kubectl works
    from the host without --insecure-skip-tls-verify.

    Returns:
        {
          "container_id": str,
          "endpoint_ip": str,          # container bridge IP (used in kubeconfig)
          "api_server_port": int,      # host-mapped port
          "certificate_authority": str, # base64-encoded CA cert
        }
    """
    if not _docker_available:
        endpoint_ip = _stub_ip("172.19.0.")
        print(f"ℹ️  Stub GKE cluster '{cluster_name}' ready (Docker unavailable)")
        return {
            "container_id": f"stub-k3s-{cluster_name}",
            "endpoint_ip": endpoint_ip,
            "api_server_port": 6443,
            "certificate_authority": "stub-ca",
        }
    import base64, urllib.request, urllib.error, ssl

    _ensure_gke_network()

    image = K3S_VERSION_MAP.get(kubernetes_version, K3S_VERSION_MAP["1.28"])
    container_name = f"gke-{cluster_name}"

    # Remove any stale container with the same name
    try:
        old = client.containers.get(container_name)
        old.remove(force=True)
        print(f"♻️  Removed stale container {container_name}")
    except docker.errors.NotFound:
        pass

    api_port = _find_free_port()
    volume_name = f"gke-{cluster_name}-data"

    print(f"🚀 Starting k3s {kubernetes_version} for cluster '{cluster_name}' on host:{api_port} …")

    container = client.containers.run(
        image,
        name=container_name,
        command=[
            "server",
            "--disable=traefik",
            "--disable=servicelb",
            "--tls-san=localhost",
            "--tls-san=127.0.0.1",
        ],
        detach=True,
        privileged=True,
        ports={"6443/tcp": api_port},
        environment={
            "K3S_KUBECONFIG_OUTPUT": "/output/kubeconfig.yaml",
            "K3S_KUBECONFIG_MODE": "666",
        },
        tmpfs={"/run": "", "/var/run": ""},
        volumes={volume_name: {"bind": "/var/lib/rancher/k3s", "mode": "rw"}},
        network=_GKE_NETWORK,
        labels={
            "gcs-stimulator": "true",
            "service": "gke",
            "gke.cluster_name": cluster_name,
            "gke.kubernetes_version": kubernetes_version,
        },
    )

    # Get container bridge IP on the GKE network
    container.reload()
    endpoint_ip = container.attrs["NetworkSettings"]["Networks"][_GKE_NETWORK]["IPAddress"]
    print(f"📍 k3s container IP: {endpoint_ip}")

    # Poll /readyz — any HTTP response (including 401) means the TCP stack is up
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    deadline = time.time() + 60
    ready = False
    while time.time() < deadline:
        try:
            urllib.request.urlopen(
                f"https://{endpoint_ip}:6443/readyz", context=ctx, timeout=3
            )
            ready = True
            break
        except urllib.error.HTTPError:
            ready = True
            break
        except Exception:
            time.sleep(2)

    if not ready:
        container.remove(force=True)
        _USED_PORTS.discard(api_port)
        raise RuntimeError(
            f"k3s API server at {endpoint_ip}:6443 did not become ready within 60s"
        )

    # Extract CA certificate for kubeconfig certificateAuthority field
    ca_data = ""
    exit_code, output = container.exec_run(
        "cat /var/lib/rancher/k3s/server/tls/server-ca.crt", demux=False
    )
    if exit_code == 0 and output:
        ca_data = base64.b64encode(output).decode("utf-8")

    print(f"✅ GKE cluster '{cluster_name}' ready at {endpoint_ip}:6443 (host port {api_port})")
    return {
        "container_id": container.id,
        "endpoint_ip": endpoint_ip,
        "api_server_port": api_port,
        "certificate_authority": ca_data,
    }


def get_k3s_kubeconfig(container_id: str, endpoint_ip: str) -> str:
    """Extract kubeconfig from k3s container and replace localhost with real IP.

    Retries for up to 30 seconds because k3s writes the file a few seconds
    after the API server starts.
    """
    if not _docker_available:
        return (
            "apiVersion: v1\n"
            "clusters:\n- cluster:\n    server: https://"
            f"{endpoint_ip}:6443\n"
            "  name: stub\n"
            "contexts:\n- context:\n    cluster: stub\n    user: stub\n  name: stub\n"
            "current-context: stub\nkind: Config\npreferences: {}\nusers:\n- name: stub\n  user:\n    token: stub-token\n"
        )
    container = client.containers.get(container_id)
    deadline = time.time() + 30
    while time.time() < deadline:
        exit_code, output = container.exec_run(
            "cat /etc/rancher/k3s/k3s.yaml", demux=False
        )
        if exit_code == 0 and output:
            kubeconfig = output.decode("utf-8")
            kubeconfig = kubeconfig.replace(
                "https://127.0.0.1:6443", f"https://{endpoint_ip}:6443"
            )
            kubeconfig = kubeconfig.replace(
                "https://localhost:6443", f"https://{endpoint_ip}:6443"
            )
            return kubeconfig
        time.sleep(2)
    raise RuntimeError("Failed to read kubeconfig from k3s container after 30s")


def stop_k3s_cluster(container_id: str) -> None:
    """Stop (but don't delete) a k3s cluster container — maps to STOPPED state."""
    if not _docker_available:
        return
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=15)
        print(f"⏹️  Stopped k3s container {container_id[:12]}")
    except docker.errors.NotFound:
        print(f"⚠️  k3s container {container_id[:12]} not found")
    except Exception as e:
        print(f"Error stopping k3s container: {e}")


def start_k3s_cluster(container_id: str) -> None:
    """Start a previously stopped k3s cluster container — back to RUNNING."""
    if not _docker_available:
        return
    try:
        container = client.containers.get(container_id)
        container.start()
        print(f"▶️  Started k3s container {container_id[:12]}")
    except docker.errors.NotFound:
        print(f"⚠️  k3s container {container_id[:12]} not found")
    except Exception as e:
        print(f"Error starting k3s container: {e}")


def delete_k3s_cluster(container_id: str, cluster_name: str = "") -> None:
    """Stop and remove a k3s cluster container and its named data volume."""
    if not _docker_available:
        return
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
        print(f"🗑️  Removed k3s container {container_id[:12]}")
    except docker.errors.NotFound:
        print(f"⚠️  k3s container {container_id[:12]} not found (already removed?)")
    except Exception as e:
        print(f"Error removing k3s container: {e}")

    if cluster_name:
        volume_name = f"gke-{cluster_name}-data"
        try:
            vol = client.volumes.get(volume_name)
            vol.remove(force=True)
            print(f"🗑️  Removed volume {volume_name}")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"Error removing volume {volume_name}: {e}")


def create_k3s_agents(
    cluster_name: str,
    server_container_id: str,
    server_ip: str,
    node_count: int,
    pool_name: str,
    kubernetes_version: str = "1.28",
) -> list:
    """Spin up k3s agent containers that join an existing k3s server.

    Returns list of container IDs for all started agent nodes.
    """
    if not _docker_available:
        return [f"stub-agent-{pool_name}-{i}" for i in range(node_count)]
    # Fetch the k3s server token from the control-plane container
    server_container = client.containers.get(server_container_id)
    deadline = time.time() + 30
    token = None
    while time.time() < deadline:
        code, out = server_container.exec_run(
            "cat /var/lib/rancher/k3s/server/node-token", demux=False
        )
        if code == 0 and out:
            token = out.decode("utf-8").strip()
            break
        time.sleep(2)
    if not token:
        raise RuntimeError("Could not retrieve k3s node-token from server container")

    image = K3S_VERSION_MAP.get(kubernetes_version, K3S_VERSION_MAP["1.28"])
    container_ids = []

    for i in range(node_count):
        agent_name = f"gke-{cluster_name}-{pool_name}-node-{i}"
        # Remove stale agent with same name
        try:
            old = client.containers.get(agent_name)
            old.remove(force=True)
        except docker.errors.NotFound:
            pass

        print(f"🔧 Starting k3s agent {agent_name} → {server_ip}:6443 …")
        agent = client.containers.run(
            image,
            name=agent_name,
            command=[
                "agent",
                f"--server=https://{server_ip}:6443",
                f"--token={token}",
            ],
            detach=True,
            privileged=True,
            tmpfs={"/run": "", "/var/run": ""},
            network=_GKE_NETWORK,
            environment={"K3S_NODE_NAME": agent_name},
            labels={
                "gcs-stimulator": "true",
                "service": "gke",
                "gke.cluster_name": cluster_name,
                "gke.pool_name": pool_name,
                "gke.node_index": str(i),
            },
        )
        container_ids.append(agent.id)
        print(f"✅ Agent node {agent_name} started (id={agent.id[:12]})")

    return container_ids


def delete_k3s_agent(container_id: str) -> None:
    """Stop and remove a k3s agent node container."""
    if not _docker_available:
        return
    try:
        c = client.containers.get(container_id)
        c.remove(force=True)
        print(f"🗑️  Removed k3s agent {container_id[:12]}")
    except docker.errors.NotFound:
        print(f"⚠️  Agent container {container_id[:12]} not found (already removed?)")
    except Exception as e:
        print(f"Error removing k3s agent {container_id[:12]}: {e}")


def resize_k3s_agents(
    cluster_name: str,
    server_container_id: str,
    server_ip: str,
    pool_name: str,
    current_container_ids: list,
    desired_count: int,
    kubernetes_version: str = "1.28",
) -> list:
    """Scale a node pool up or down to desired_count worker nodes.

    Returns the updated list of container IDs.
    """
    if not _docker_available:
        current_ids = list(current_container_ids or [])
        if desired_count <= len(current_ids):
            return current_ids[:desired_count]
        # Add deterministic stub IDs when scaling up in stub mode.
        next_idx = len(current_ids)
        for idx in range(next_idx, desired_count):
            current_ids.append(f"stub-agent-{pool_name}-{idx}")
        return current_ids

    current_count = len(current_container_ids)

    if desired_count > current_count:
        # Scale UP: create extra agents with indices starting after existing ones
        add_count = desired_count - current_count
        image = K3S_VERSION_MAP.get(kubernetes_version, K3S_VERSION_MAP["1.28"])
        server_container = client.containers.get(server_container_id)
        token = None
        deadline = time.time() + 20
        while time.time() < deadline:
            code, out = server_container.exec_run(
                "cat /var/lib/rancher/k3s/server/node-token", demux=False
            )
            if code == 0 and out:
                token = out.decode("utf-8").strip()
                break
            time.sleep(2)
        if not token:
            raise RuntimeError("Could not retrieve k3s node-token")

        new_ids = list(current_container_ids)
        for offset in range(add_count):
            idx = current_count + offset
            agent_name = f"gke-{cluster_name}-{pool_name}-node-{idx}"
            try:
                old = client.containers.get(agent_name)
                old.remove(force=True)
            except docker.errors.NotFound:
                pass
            print(f"➕ Scaling up: starting agent {agent_name}")
            agent = client.containers.run(
                image,
                name=agent_name,
                command=["agent", f"--server=https://{server_ip}:6443", f"--token={token}"],
                detach=True,
                privileged=True,
                tmpfs={"/run": "", "/var/run": ""},
                network=_GKE_NETWORK,
                environment={"K3S_NODE_NAME": agent_name},
                labels={
                    "gcs-stimulator": "true", "service": "gke",
                    "gke.cluster_name": cluster_name, "gke.pool_name": pool_name,
                    "gke.node_index": str(idx),
                },
            )
            new_ids.append(agent.id)
            print(f"✅ Scale-up agent {agent_name} started")
        return new_ids

    elif desired_count < current_count:
        # Scale DOWN: remove containers from the tail
        to_remove = current_container_ids[desired_count:]
        for cid in to_remove:
            delete_k3s_agent(cid)
        return current_container_ids[:desired_count]

    return current_container_ids  # no change


def run_kubectl_command(kubeconfig_yaml: str, command: str) -> dict:
    """Execute a kubectl command against a cluster using its stored kubeconfig.

    Args:
        kubeconfig_yaml: Full kubeconfig YAML string from the DB.
        command: kubectl args string, e.g. "get pods -A" or "get nodes -o wide"

    Returns:
        {"stdout": str, "stderr": str, "exit_code": int}
    """
    import subprocess, tempfile, os, shlex

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(kubeconfig_yaml)
        kc_path = f.name
    try:
        args = ["kubectl", "--kubeconfig", kc_path] + shlex.split(command)
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "kubectl command timed out (15s)", "exit_code": 1}
    finally:
        os.unlink(kc_path)


# ─── Cloud Run + Artifact Registry helpers ────────────────────────────────────

_CLOUD_RUN_PORT_RANGE = range(18080, 18280)
_USED_RUN_PORTS: set[int] = set()
_REGISTRY_CONTAINER = "gcs-stimulator-registry"


def _find_free_run_port() -> int:
    if not _docker_available:
        return random.choice(list(_CLOUD_RUN_PORT_RANGE))
    import socket
    for port in _CLOUD_RUN_PORT_RANGE:
        if port in _USED_RUN_PORTS:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                _USED_RUN_PORTS.add(port)
                return port
            except OSError:
                continue
    raise RuntimeError("No free port available in Cloud Run range 18080-18279")


def ensure_local_registry() -> Dict[str, str]:
    """Ensure local Docker registry exists on localhost:5000."""
    if not _docker_available:
        return {
            "container_id": "stub-registry",
            "endpoint": "localhost:5000",
            "status": "RUNNING",
        }
    try:
        c = client.containers.get(_REGISTRY_CONTAINER)
        if c.status != "running":
            c.start()
        return {"container_id": c.id, "endpoint": "localhost:5000", "status": "RUNNING"}
    except docker.errors.NotFound:
        pass

    c = client.containers.run(
        "registry:2",
        name=_REGISTRY_CONTAINER,
        detach=True,
        ports={"5000/tcp": 5000},
        restart_policy={"Name": "unless-stopped"},
        labels={"gcs-stimulator": "true", "service": "artifact-registry"},
    )
    return {"container_id": c.id, "endpoint": "localhost:5000", "status": "RUNNING"}


_FAKE_GCS_CONTAINER = "gcs-stimulator-fake-gcs-server"
_FAKE_GCS_PORT = 4443


def ensure_fake_gcs_server() -> Dict[str, str]:
    """Ensure a real fake-gcs-server (fsouza/fake-gcs-server) container is
    running on localhost:4443. This is what gives Cloud Storage genuine GCS
    wire-protocol fidelity (real JSON/XML/resumable-upload semantics) instead
    of a hand-rolled approximation — see CLAUDE.md's decisions log."""
    if not _docker_available:
        return {
            "container_id": "stub-fake-gcs",
            "endpoint": f"http://localhost:{_FAKE_GCS_PORT}",
            "status": "RUNNING",
        }
    try:
        c = client.containers.get(_FAKE_GCS_CONTAINER)
        if c.status != "running":
            c.start()
        return {"container_id": c.id, "endpoint": f"http://localhost:{_FAKE_GCS_PORT}", "status": "RUNNING"}
    except docker.errors.NotFound:
        pass

    c = client.containers.run(
        "fsouza/fake-gcs-server",
        name=_FAKE_GCS_CONTAINER,
        command=["-scheme", "http", "-public-host", f"localhost:{_FAKE_GCS_PORT}"],
        detach=True,
        ports={f"{_FAKE_GCS_PORT}/tcp": _FAKE_GCS_PORT},
        restart_policy={"Name": "unless-stopped"},
        labels={"gcs-stimulator": "true", "service": "storage-backend"},
    )
    return {"container_id": c.id, "endpoint": f"http://localhost:{_FAKE_GCS_PORT}", "status": "RUNNING"}


def normalize_registry_image(image: str, project_id: str) -> str:
    """Translate gcr.io/pkg.dev style names to localhost:5000 for local pulls."""
    stripped = image.strip()
    if stripped.startswith("localhost:5000/"):
        return stripped

    # gcr.io/{project}/path:tag -> localhost:5000/{project}/path:tag
    if stripped.startswith("gcr.io/"):
        parts = stripped.split("/", 2)
        if len(parts) >= 3:
            return f"localhost:5000/{parts[1]}/{parts[2]}"
        return f"localhost:5000/{project_id}/image:latest"

    # {region}-docker.pkg.dev/{project}/{repo}/path:tag -> localhost:5000/{project}/{repo}/path:tag
    if ".pkg.dev/" in stripped:
        after = stripped.split(".pkg.dev/", 1)[1]
        return f"localhost:5000/{after}"

    return stripped


def _as_env_list(env_vars: List[Dict[str, str]]) -> Dict[str, str]:
    env = {}
    for item in env_vars or []:
        name = item.get("name")
        if not name:
            continue
        env[name] = str(item.get("value", ""))
    return env


def deploy_cloud_run_container(
    service_name: str,
    revision_name: str,
    image: str,
    env_vars: List[Dict[str, str]],
    container_port: int = 8080,
) -> Dict[str, object]:
    """Run a Cloud Run revision as a local Docker container."""
    if not _docker_available:
        host_port = _find_free_run_port()
        return {
            "container_id": f"stub-run-{revision_name}",
            "container_name": f"run-{service_name}-{revision_name}",
            "host_port": host_port,
            "url": f"http://localhost:{host_port}",
        }

    host_port = _find_free_run_port()
    container_name = f"run-{service_name}-{revision_name}"

    try:
        old = client.containers.get(container_name)
        old.remove(force=True)
    except docker.errors.NotFound:
        pass

    try:
        client.images.pull(image)
    except Exception:
        # Keep going; image might already exist locally or be build-only.
        pass

    env = _as_env_list(env_vars)
    env["PORT"] = str(container_port)

    c = client.containers.run(
        image,
        name=container_name,
        detach=True,
        environment=env,
        ports={f"{container_port}/tcp": host_port},
        labels={
            "gcs-stimulator": "true",
            "service": "cloud-run",
            "run.service": service_name,
            "run.revision": revision_name,
        },
    )
    return {
        "container_id": c.id,
        "container_name": container_name,
        "host_port": host_port,
        "url": f"http://localhost:{host_port}",
    }


def delete_cloud_run_revision_container(container_id: Optional[str]) -> None:
    if not container_id:
        return
    if not _docker_available:
        return
    try:
        c = client.containers.get(container_id)
        c.remove(force=True)
    except Exception:
        return


def create_data_service_container(
    name: str,
    image: str,
    env: Optional[Dict[str, str]] = None,
    ports: Optional[Dict[str, int]] = None,
    network: str = "gcp-default",
) -> Dict[str, Optional[str]]:
    """Create a generic data-backing container (Cloud SQL, Memorystore, ...).

    Unlike create_container(), this supports environment variables and
    published ports, since these services need to be reachable from the
    host (e.g. `psql -h localhost -p <port>`), not just from other
    containers on the Docker network.

    Returns: {"container_id", "container_name", "internal_ip", "host_port"}
    """
    container_name = f"gcp-svc-{name}"

    if not _docker_available:
        internal_ip = _stub_ip()
        host_port = list(ports.values())[0] if ports else None
        return {
            "container_id": f"stub-{container_name}",
            "container_name": container_name,
            "internal_ip": internal_ip,
            "host_port": host_port,
        }

    try:
        existing = client.containers.get(container_name)
        raise RuntimeError(f"Container name '{container_name}' already in use (id={existing.id[:12]})")
    except docker.errors.NotFound:
        pass

    try:
        client.networks.get(network)
    except Exception:
        create_default_network()

    port_bindings = {f"{container_port}/tcp": None for container_port in (ports or {}).values()}

    try:
        container = client.containers.run(
            image,
            name=container_name,
            environment=env or {},
            ports=port_bindings or None,
            detach=True,
            network=network,
            hostname=name,
        )
    except docker.errors.APIError as e:
        raise RuntimeError(f"Failed to create container '{container_name}': {e}")

    container.reload()
    internal_ip = container.attrs.get("NetworkSettings", {}).get("Networks", {}).get(network, {}).get("IPAddress")

    host_port = None
    if ports:
        container_port = list(ports.values())[0]
        bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {}).get(f"{container_port}/tcp")
        if bindings:
            host_port = int(bindings[0]["HostPort"])

    return {
        "container_id": container.id,
        "container_name": container_name,
        "internal_ip": internal_ip,
        "host_port": host_port,
    }


def stop_data_service_container(container_id: str) -> None:
    if not _docker_available or not container_id or container_id.startswith("stub-"):
        return
    try:
        client.containers.get(container_id).stop()
    except Exception:
        pass


def start_data_service_container(container_id: str) -> None:
    if not _docker_available or not container_id or container_id.startswith("stub-"):
        return
    try:
        client.containers.get(container_id).start()
    except Exception:
        pass


def delete_data_service_container(container_id: str) -> None:
    if not _docker_available or not container_id or container_id.startswith("stub-"):
        return
    try:
        client.containers.get(container_id).remove(force=True)
    except Exception:
        pass


# Initialize default network
create_default_network()
print("✅ Docker manager initialized")
