"""
Cloud Tasks API endpoints.

Implements a subset of cloudtasks.googleapis.com/v2: queues and tasks,
with a background dispatcher thread that performs each task's HTTP request
when its schedule_time arrives (or immediately, by default).
"""

from typing import Any, Dict
import logging

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from .storage import storage
from .models import QueueState

logger = logging.getLogger(__name__)
router = APIRouter()

storage.start_dispatcher()


@router.post("/projects/{project}/locations/{location}/queues")
async def create_queue(project: str, location: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name", "")
    queue_id = name.rsplit("/", 1)[-1] if name else body.get("queueId")
    if not queue_id:
        raise HTTPException(400, "queue name or queueId is required")
    try:
        queue = storage.create_queue(project, location, queue_id)
        return queue.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/locations/{location}/queues")
async def list_queues(project: str, location: str) -> Dict[str, Any]:
    queues = storage.list_queues(project, location)
    return {"queues": [q.to_dict() for q in queues]}


@router.get("/projects/{project}/locations/{location}/queues/{queue}")
async def get_queue(project: str, location: str, queue: str) -> Dict[str, Any]:
    q = storage.get_queue(project, location, queue)
    if not q:
        raise HTTPException(404, f"Queue '{queue}' not found")
    return q.to_dict()


@router.delete("/projects/{project}/locations/{location}/queues/{queue}")
async def delete_queue(project: str, location: str, queue: str) -> Dict[str, Any]:
    if not storage.delete_queue(project, location, queue):
        raise HTTPException(404, f"Queue '{queue}' not found")
    return {}


@router.post("/projects/{project}/locations/{location}/queues/{queue}:pause")
async def pause_queue(project: str, location: str, queue: str) -> Dict[str, Any]:
    q = storage.pause_queue(project, location, queue)
    if not q:
        raise HTTPException(404, f"Queue '{queue}' not found")
    return q.to_dict()


@router.post("/projects/{project}/locations/{location}/queues/{queue}:resume")
async def resume_queue(project: str, location: str, queue: str) -> Dict[str, Any]:
    q = storage.resume_queue(project, location, queue)
    if not q:
        raise HTTPException(404, f"Queue '{queue}' not found")
    return q.to_dict()


@router.post("/projects/{project}/locations/{location}/queues/{queue}/tasks")
async def create_task(project: str, location: str, queue: str, body: Dict[str, Any]) -> Dict[str, Any]:
    task_body = body.get("task", body)
    http_request = task_body.get("httpRequest", {})
    schedule_time_str = task_body.get("scheduleTime")
    schedule_time = None
    if schedule_time_str:
        try:
            schedule_time = datetime.fromisoformat(schedule_time_str.replace("Z", "+00:00"))
        except ValueError:
            schedule_time = None
    try:
        task = storage.create_task(project, location, queue, http_request, schedule_time)
        return task.to_dict()
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/projects/{project}/locations/{location}/queues/{queue}/tasks")
async def list_tasks(project: str, location: str, queue: str) -> Dict[str, Any]:
    tasks = storage.list_tasks(project, location, queue)
    return {"tasks": [t.to_dict() for t in tasks]}


@router.get("/projects/{project}/locations/{location}/queues/{queue}/tasks/{task}")
async def get_task(project: str, location: str, queue: str, task: str) -> Dict[str, Any]:
    t = storage.get_task(project, location, queue, task)
    if not t:
        raise HTTPException(404, f"Task '{task}' not found")
    return t.to_dict()


@router.delete("/projects/{project}/locations/{location}/queues/{queue}/tasks/{task}")
async def delete_task(project: str, location: str, queue: str, task: str) -> Dict[str, Any]:
    if not storage.delete_task(project, location, queue, task):
        raise HTTPException(404, f"Task '{task}' not found")
    return {}


@router.post("/projects/{project}/locations/{location}/queues/{queue}/tasks/{task}:run")
async def run_task(project: str, location: str, queue: str, task: str) -> Dict[str, Any]:
    t = storage.run_task_now(project, location, queue, task)
    if not t:
        raise HTTPException(404, f"Task '{task}' not found")
    return t.to_dict()


@router.get("/tasks/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
