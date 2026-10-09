"""Cloud Tasks data models: queues and tasks."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import uuid
import base64


class QueueState:
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class TaskState:
    SCHEDULED = "SCHEDULED"
    DISPATCHED = "DISPATCHED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class Task:
    queue_id: str
    project_id: str
    location: str
    task_id: str
    http_request: Dict[str, Any] = field(default_factory=dict)
    schedule_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dispatch_count: int = 0
    response_count: int = 0
    state: str = TaskState.SCHEDULED
    last_attempt_result: Optional[str] = None

    @property
    def name(self) -> str:
        return (
            f"projects/{self.project_id}/locations/{self.location}/"
            f"queues/{self.queue_id}/tasks/{self.task_id}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "httpRequest": self.http_request,
            "scheduleTime": self.schedule_time.isoformat() + "Z",
            "createTime": self.create_time.isoformat() + "Z",
            "dispatchCount": self.dispatch_count,
            "responseCount": self.response_count,
            "view": "BASIC",
            "state": self.state,
            "lastAttemptResult": self.last_attempt_result,
        }


@dataclass
class Queue:
    queue_id: str
    project_id: str
    location: str
    state: str = QueueState.RUNNING
    max_dispatches_per_second: float = 500.0
    max_concurrent_dispatches: int = 1000
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tasks: Dict[str, Task] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/queues/{self.queue_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "rateLimits": {
                "maxDispatchesPerSecond": self.max_dispatches_per_second,
                "maxConcurrentDispatches": self.max_concurrent_dispatches,
            },
            "purgeTime": None,
        }

    def new_task_id(self) -> str:
        return uuid.uuid4().hex
