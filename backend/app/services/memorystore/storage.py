"""In-memory storage + Docker lifecycle for Memorystore (Redis) instances."""

from typing import Dict, List, Optional
import logging
import threading

from .models import RedisInstance, InstanceState, REDIS_IMAGE, REDIS_PORT
from app.core import docker_manager

logger = logging.getLogger(__name__)


class MemorystoreStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.instances: Dict[str, Dict[str, RedisInstance]] = {}

    def create_instance(
        self, project_id: str, instance_id: str, region: str,
        tier: str = "BASIC", memory_size_gb: int = 1, labels: Optional[Dict[str, str]] = None,
    ) -> RedisInstance:
        with self._lock:
            project_instances = self.instances.setdefault(project_id, {})
            if instance_id in project_instances:
                raise ValueError(f"Instance '{instance_id}' already exists")
            instance = RedisInstance(
                instance_id=instance_id, project_id=project_id, region=region,
                tier=tier, memory_size_gb=memory_size_gb, labels=labels or {},
            )
            project_instances[instance_id] = instance

        self._provision(instance)
        return instance

    def _provision(self, instance: RedisInstance):
        try:
            result = docker_manager.create_data_service_container(
                name=f"redis-{instance.project_id}-{instance.instance_id}",
                image=REDIS_IMAGE,
                ports={"redis": REDIS_PORT},
            )
            instance.container_id = result["container_id"]
            instance.host = result["internal_ip"]
            instance.host_port = result["host_port"]
            instance.state = InstanceState.READY
        except Exception as e:
            logger.error(f"Failed to provision Memorystore instance {instance.instance_id}: {e}")
            instance.state = InstanceState.FAILED

    def get_instance(self, project_id: str, instance_id: str) -> Optional[RedisInstance]:
        return self.instances.get(project_id, {}).get(instance_id)

    def list_instances(self, project_id: str) -> List[RedisInstance]:
        return list(self.instances.get(project_id, {}).values())

    def delete_instance(self, project_id: str, instance_id: str) -> bool:
        instance = self.get_instance(project_id, instance_id)
        if not instance:
            return False
        docker_manager.delete_data_service_container(instance.container_id)
        with self._lock:
            del self.instances[project_id][instance_id]
        return True

    def get_stats(self) -> Dict[str, int]:
        return {"instances": sum(len(i) for i in self.instances.values())}


storage = MemorystoreStorage()
