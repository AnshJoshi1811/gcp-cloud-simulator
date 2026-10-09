"""Memorystore data models: Redis instances."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class InstanceTier:
    BASIC = "BASIC"
    STANDARD_HA = "STANDARD_HA"


class InstanceState:
    CREATING = "CREATING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"


REDIS_IMAGE = "redis:7-alpine"
REDIS_PORT = 6379


@dataclass
class RedisInstance:
    instance_id: str
    project_id: str
    region: str
    tier: str = InstanceTier.BASIC
    memory_size_gb: int = 1
    redis_version: str = "REDIS_7_0"
    state: str = InstanceState.CREATING
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    container_id: Optional[str] = None
    host: Optional[str] = None
    port: int = REDIS_PORT
    host_port: Optional[int] = None
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.region}/instances/{self.instance_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier,
            "memorySizeGb": self.memory_size_gb,
            "redisVersion": self.redis_version,
            "state": self.state,
            "createTime": self.create_time.isoformat() + "Z",
            "host": self.host,
            "port": self.port,
            "hostPort": self.host_port,
            "labels": self.labels,
        }
