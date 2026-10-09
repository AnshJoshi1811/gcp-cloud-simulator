"""Cloud Functions data models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class FunctionState:
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    DELETING = "DELETING"


SUPPORTED_RUNTIMES = ("python312", "python311", "python310")


@dataclass
class CloudFunction:
    project_id: str
    location: str
    name: str
    entry_point: str
    source_code: str
    runtime: str = "python312"
    state: str = FunctionState.DEPLOYING
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    update_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    container_id: Optional[str] = None
    host_port: Optional[int] = None
    invocation_count: int = 0
    last_error: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/functions/{self.name}"

    @property
    def https_trigger_url(self) -> str:
        return f"http://localhost:8080/functions/v1/invoke/{self.project_id}/{self.location}/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.full_name,
            "entryPoint": self.entry_point,
            "runtime": self.runtime,
            "state": self.state,
            "updateTime": self.update_time.isoformat() + "Z",
            "httpsTrigger": {"url": self.https_trigger_url},
            "environmentVariables": self.environment_variables,
            "invocationCount": self.invocation_count,
            "lastError": self.last_error,
        }
