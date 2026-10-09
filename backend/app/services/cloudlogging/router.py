"""
Cloud Logging API endpoints.

Implements a subset of logging.googleapis.com/v2: entries.write, entries.list,
and sinks CRUD, with a practical subset of the logging filter query language
(severity, logName, resource.type).
"""

from typing import Any, Dict
import logging as stdlib_logging

from fastapi import APIRouter, HTTPException

from .storage import storage
from .models import Severity

logger = stdlib_logging.getLogger(__name__)
router = APIRouter()


def _project_from_resource_name(name: str) -> str:
    # "projects/{project}" or "projects/{project}/logs/{logId}"
    parts = name.split("/")
    if len(parts) >= 2 and parts[0] == "projects":
        return parts[1]
    return name


@router.post("/entries:write")
async def write_entries(body: Dict[str, Any]) -> Dict[str, Any]:
    log_name = body.get("logName", "")
    default_resource = body.get("resource", {})
    default_labels = body.get("labels", {})
    entries = body.get("entries", [{}])

    written = []
    for entry in entries:
        entry_log_name = entry.get("logName", log_name)
        if not entry_log_name:
            raise HTTPException(400, "logName is required")
        project_id = _project_from_resource_name(entry_log_name)
        log_id = entry_log_name.split("/logs/")[-1] if "/logs/" in entry_log_name else entry_log_name

        severity = entry.get("severity", Severity.DEFAULT)
        resource = entry.get("resource", default_resource)
        labels = {**default_labels, **entry.get("labels", {})}

        saved = storage.write_entry(
            project_id=project_id,
            log_name=log_id,
            severity=severity,
            text_payload=entry.get("textPayload"),
            json_payload=entry.get("jsonPayload"),
            resource_type=resource.get("type", "global"),
            labels=labels,
        )
        written.append(saved.to_dict())

    return {}


@router.post("/entries:list")
async def list_entries(body: Dict[str, Any]) -> Dict[str, Any]:
    resource_names = body.get("resourceNames", [])
    project_ids = [_project_from_resource_name(n) for n in resource_names] or ["default"]
    filter_str = body.get("filter", "")
    page_size = body.get("pageSize", 100)
    order_by = body.get("orderBy", "timestamp desc")

    entries = storage.list_entries(project_ids, filter_str, page_size, order_by)
    return {"entries": [e.to_dict() for e in entries], "nextPageToken": None}


@router.post("/projects/{project}/sinks")
async def create_sink(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    sink_id = body.get("name")
    destination = body.get("destination")
    if not sink_id or not destination:
        raise HTTPException(400, "name and destination are required")
    try:
        sink = storage.create_sink(project, sink_id, destination, body.get("filter", ""))
        return sink.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/sinks")
async def list_sinks(project: str) -> Dict[str, Any]:
    return {"sinks": [s.to_dict() for s in storage.list_sinks(project)]}


@router.get("/projects/{project}/sinks/{sink}")
async def get_sink(project: str, sink: str) -> Dict[str, Any]:
    s = storage.get_sink(project, sink)
    if not s:
        raise HTTPException(404, f"Sink '{sink}' not found")
    return s.to_dict()


@router.delete("/projects/{project}/sinks/{sink}")
async def delete_sink(project: str, sink: str) -> Dict[str, Any]:
    if not storage.delete_sink(project, sink):
        raise HTTPException(404, f"Sink '{sink}' not found")
    return {}


@router.get("/logging/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
