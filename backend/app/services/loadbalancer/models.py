"""Cloud Load Balancing data models: health checks, backend services, URL maps,
target proxies, and forwarding rules."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class HealthCheck:
    project_id: str
    name: str
    port: int = 80
    check_interval_sec: int = 5
    timeout_sec: int = 5
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def self_link(self) -> str:
        return f"projects/{self.project_id}/global/healthChecks/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "selfLink": self.self_link,
            "port": self.port,
            "checkIntervalSec": self.check_interval_sec,
            "timeoutSec": self.timeout_sec,
            "creationTimestamp": self.create_time.isoformat() + "Z",
        }


@dataclass
class Backend:
    instance_name: str
    zone: str
    port: int = 80


@dataclass
class BackendService(object):
    project_id: str
    name: str
    protocol: str = "HTTP"
    port_name: str = "http"
    health_checks: List[str] = field(default_factory=list)
    backends: List[Backend] = field(default_factory=list)
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def self_link(self) -> str:
        return f"projects/{self.project_id}/global/backendServices/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "selfLink": self.self_link,
            "protocol": self.protocol,
            "portName": self.port_name,
            "healthChecks": self.health_checks,
            "backends": [
                {"instanceName": b.instance_name, "zone": b.zone, "port": b.port}
                for b in self.backends
            ],
            "creationTimestamp": self.create_time.isoformat() + "Z",
        }


@dataclass
class UrlMap:
    project_id: str
    name: str
    default_service: str
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def self_link(self) -> str:
        return f"projects/{self.project_id}/global/urlMaps/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "selfLink": self.self_link,
            "defaultService": self.default_service,
            "creationTimestamp": self.create_time.isoformat() + "Z",
        }


@dataclass
class TargetHttpProxy:
    project_id: str
    name: str
    url_map: str
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def self_link(self) -> str:
        return f"projects/{self.project_id}/global/targetHttpProxies/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "selfLink": self.self_link,
            "urlMap": self.url_map,
            "creationTimestamp": self.create_time.isoformat() + "Z",
        }


@dataclass
class ForwardingRule:
    project_id: str
    name: str
    target: str
    ip_address: str
    port_range: str = "80"
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def self_link(self) -> str:
        return f"projects/{self.project_id}/global/forwardingRules/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "selfLink": self.self_link,
            "IPAddress": self.ip_address,
            "portRange": self.port_range,
            "target": self.target,
            "creationTimestamp": self.create_time.isoformat() + "Z",
        }
