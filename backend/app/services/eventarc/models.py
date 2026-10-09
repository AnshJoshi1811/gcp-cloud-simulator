"""Event Routing (Eventarc-style) data models: triggers."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class TriggerState:
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"


@dataclass
class Trigger:
    project_id: str
    location: str
    trigger_id: str
    topic: str  # Pub/Sub topic name this trigger listens on
    destination_function: str  # Cloud Function name to invoke per event
    # internal: the dedicated Pub/Sub subscription created for this trigger
    subscription_id: str = ""
    state: str = TriggerState.ACTIVE
    event_count: int = 0
    last_error: Optional[str] = None
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/triggers/{self.trigger_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "eventFilters": [{"attribute": "type", "value": "google.cloud.pubsub.topic.v1.messagePublished"}],
            "transport": {"pubsub": {"topic": self.topic}},
            "destination": {"cloudFunction": self.destination_function},
            "state": self.state,
            "eventCount": self.event_count,
            "lastError": self.last_error,
            "createTime": self.create_time.isoformat() + "Z",
        }
