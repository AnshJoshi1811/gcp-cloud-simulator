"""
Event Routing (Eventarc-style) API endpoints.

Implements a practical subset of eventarc.googleapis.com/v1: triggers that
bind a Pub/Sub topic to a Cloud Function destination. A background
dispatcher (storage.py) actually pulls published messages and invokes the
destination function — this is live Pub/Sub -> Cloud Functions routing, not
bookkeeping.
"""

from typing import Any, Dict
import logging

from fastapi import APIRouter, HTTPException

from .storage import storage

logger = logging.getLogger(__name__)
router = APIRouter()

storage.start_dispatcher()


@router.post("/projects/{project}/locations/{location}/triggers")
async def create_trigger(project: str, location: str, body: Dict[str, Any]) -> Dict[str, Any]:
    trigger_id = body.get("triggerId") or body.get("name")
    topic = body.get("topic")
    destination_function = body.get("destinationFunction")
    if not trigger_id or not topic or not destination_function:
        raise HTTPException(400, "triggerId, topic, and destinationFunction are required")
    try:
        trigger = storage.create_trigger(project, location, trigger_id, topic, destination_function)
        return trigger.to_dict()
    except ValueError as e:
        code = 409 if "already exists" in str(e) else 404
        raise HTTPException(code, str(e))


@router.get("/projects/{project}/locations/{location}/triggers")
async def list_triggers(project: str, location: str) -> Dict[str, Any]:
    return {"triggers": [t.to_dict() for t in storage.list_triggers(project)]}


@router.get("/projects/{project}/locations/{location}/triggers/{trigger_id}")
async def get_trigger(project: str, location: str, trigger_id: str) -> Dict[str, Any]:
    trigger = storage.get_trigger(project, trigger_id)
    if not trigger:
        raise HTTPException(404, f"Trigger '{trigger_id}' not found")
    return trigger.to_dict()


@router.delete("/projects/{project}/locations/{location}/triggers/{trigger_id}")
async def delete_trigger(project: str, location: str, trigger_id: str) -> Dict[str, Any]:
    if not storage.delete_trigger(project, trigger_id):
        raise HTTPException(404, f"Trigger '{trigger_id}' not found")
    return {}


@router.get("/eventarc/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
