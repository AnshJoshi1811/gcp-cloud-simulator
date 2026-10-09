"""Cloud Logging data models: log entries and sinks."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


class Severity:
    DEFAULT = "DEFAULT"
    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"

    ORDER = [DEFAULT, DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL, ALERT, EMERGENCY]

    @classmethod
    def rank(cls, severity: str) -> int:
        try:
            return cls.ORDER.index(severity)
        except ValueError:
            return 0


@dataclass
class LogEntry:
    project_id: str
    log_name: str
    insert_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    severity: str = Severity.DEFAULT
    text_payload: Optional[str] = None
    json_payload: Optional[Dict[str, Any]] = None
    resource_type: str = "global"
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "logName": f"projects/{self.project_id}/logs/{self.log_name}",
            "resource": {"type": self.resource_type, "labels": {}},
            "timestamp": self.timestamp.isoformat() + "Z",
            "severity": self.severity,
            "insertId": self.insert_id,
            "labels": self.labels,
        }
        if self.json_payload is not None:
            data["jsonPayload"] = self.json_payload
        else:
            data["textPayload"] = self.text_payload or ""
        return data


@dataclass
class LogSink:
    project_id: str
    sink_id: str
    destination: str
    filter: str = ""
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return f"projects/{self.project_id}/sinks/{self.sink_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "destination": self.destination,
            "filter": self.filter,
            "createTime": self.create_time.isoformat() + "Z",
        }
