"""API Gateway data models: API configs, gateways, and routes."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Route:
    path: str  # e.g. "/hello" — matched as an exact path or a prefix ending in "*"
    method: str = "ANY"
    backend_function: Optional[str] = None  # "<function-name>" in the same project/location
    backend_url: Optional[str] = None  # arbitrary URL, for routing outside Cloud Functions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "backendFunction": self.backend_function,
            "backendUrl": self.backend_url,
        }

    def matches(self, path: str, method: str) -> bool:
        if self.method != "ANY" and self.method.upper() != method.upper():
            return False
        if self.path.endswith("*"):
            return path.startswith(self.path[:-1])
        return path == self.path


@dataclass
class ApiConfig:
    project_id: str
    api_id: str
    config_id: str
    routes: List[Route] = field(default_factory=list)
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return f"projects/{self.project_id}/apis/{self.api_id}/configs/{self.config_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "routes": [r.to_dict() for r in self.routes],
            "createTime": self.create_time.isoformat() + "Z",
        }


@dataclass
class Gateway:
    project_id: str
    location: str
    gateway_id: str
    api_config: str  # name of the ApiConfig in use
    state: str = "ACTIVE"
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/gateways/{self.gateway_id}"

    @property
    def default_hostname(self) -> str:
        return f"localhost:8080/apigateway/v1/invoke/{self.project_id}/{self.gateway_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "apiConfig": self.api_config,
            "state": self.state,
            "defaultHostname": self.default_hostname,
            "createTime": self.create_time.isoformat() + "Z",
        }
