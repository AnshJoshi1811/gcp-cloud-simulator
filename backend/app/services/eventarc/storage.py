"""In-memory storage + background dispatcher for Event Routing triggers.

Each trigger creates a dedicated Pub/Sub pull subscription on its topic; a
background thread polls every trigger's subscription, and for each message it
pulls, invokes the trigger's destination Cloud Function with the decoded
message as the request body, then acknowledges it. This is real cross-service
wiring (Pub/Sub -> Functions), not a static mapping.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import base64
import json
import logging
import threading
import time
import uuid

from .models import Trigger, TriggerState
# Pub/Sub's shared storage singleton lives in router.py, not storage.py.
from app.services.pubsub.router import storage as pubsub_storage
from app.services.functions.storage import storage as functions_storage

logger = logging.getLogger(__name__)


class EventarcStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.triggers: Dict[str, Dict[str, Trigger]] = {}  # project_id -> trigger_id -> Trigger
        self._dispatcher_started = False

    def create_trigger(
        self, project_id: str, location: str, trigger_id: str, topic: str, destination_function: str
    ) -> Trigger:
        if not pubsub_storage.topic_exists(project_id, topic):
            raise ValueError(f"Pub/Sub topic '{topic}' not found")

        with self._lock:
            bucket = self.triggers.setdefault(project_id, {})
            if trigger_id in bucket:
                raise ValueError(f"Trigger '{trigger_id}' already exists")

            subscription_id = f"eventarc-{trigger_id}-{uuid.uuid4().hex[:8]}"
            pubsub_storage.create_subscription(project_id, subscription_id, topic)

            trigger = Trigger(
                project_id=project_id, location=location, trigger_id=trigger_id,
                topic=topic, destination_function=destination_function,
                subscription_id=subscription_id,
            )
            bucket[trigger_id] = trigger
            return trigger

    def get_trigger(self, project_id: str, trigger_id: str) -> Optional[Trigger]:
        return self.triggers.get(project_id, {}).get(trigger_id)

    def list_triggers(self, project_id: str) -> List[Trigger]:
        return list(self.triggers.get(project_id, {}).values())

    def delete_trigger(self, project_id: str, trigger_id: str) -> bool:
        trigger = self.get_trigger(project_id, trigger_id)
        if not trigger:
            return False
        pubsub_storage.delete_subscription(project_id, trigger.subscription_id)
        with self._lock:
            del self.triggers[project_id][trigger_id]
        return True

    def _dispatch_once(self):
        for project_id, triggers in list(self.triggers.items()):
            for trigger in list(triggers.values()):
                pulled = pubsub_storage.pull_messages(project_id, trigger.subscription_id, max_messages=10)
                if not pulled:
                    continue
                ack_ids = []
                for item in pulled:
                    message = item["message"]
                    try:
                        data = base64.b64decode(message.get("data", "")).decode("utf-8", errors="replace")
                        try:
                            body = json.loads(data)
                        except ValueError:
                            body = {"data": data}
                        body["_eventAttributes"] = message.get("attributes", {})

                        _, status, error = functions_storage.invoke_function(
                            project_id, trigger.location, trigger.destination_function, body
                        )
                        trigger.event_count += 1
                        if error:
                            trigger.state = TriggerState.FAILED
                            trigger.last_error = error
                        else:
                            trigger.state = TriggerState.ACTIVE
                    except Exception as e:
                        trigger.state = TriggerState.FAILED
                        trigger.last_error = str(e)
                        logger.error(f"Event dispatch failed for trigger {trigger.trigger_id}: {e}")
                    ack_ids.append(item["ackId"])
                pubsub_storage.acknowledge_messages(project_id, trigger.subscription_id, ack_ids)

    def _dispatcher_loop(self):
        while True:
            try:
                self._dispatch_once()
            except Exception:
                logger.exception("eventarc dispatcher iteration failed")
            time.sleep(1)

    def start_dispatcher(self):
        if self._dispatcher_started:
            return
        self._dispatcher_started = True
        thread = threading.Thread(target=self._dispatcher_loop, daemon=True)
        thread.start()

    def get_stats(self) -> Dict[str, int]:
        return {"triggers": sum(len(t) for t in self.triggers.values())}


storage = EventarcStorage()
