"""
Cloud Functions API endpoints.

Implements a subset of cloudfunctions.googleapis.com/v1: deploy (generateUploadUrl
is skipped — source is sent inline as a string, since there's no real GCS upload
flow here), get/list/delete, and an HTTP invoke endpoint that actually executes
the function (container-backed when Docker is available, in-process otherwise).
Python-only for now (see CLAUDE.md's decisions log) — a clear 400 for unsupported runtimes.
"""

from typing import Any, Dict, Optional
import logging

from fastapi import APIRouter, HTTPException, Body

from .storage import storage
from .models import SUPPORTED_RUNTIMES

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project}/locations/{location}/functions")
async def deploy_function(project: str, location: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    entry_point = body.get("entryPoint")
    source_code = body.get("sourceCode")
    if not name or not entry_point or source_code is None:
        raise HTTPException(400, "name, entryPoint, and sourceCode are required")
    runtime = body.get("runtime", "python312")
    env_vars = body.get("environmentVariables", {})

    try:
        fn = storage.deploy_function(project, location, name, entry_point, source_code, runtime, env_vars)
        return fn.to_dict()
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/projects/{project}/locations/{location}/functions")
async def list_functions(project: str, location: str) -> Dict[str, Any]:
    return {"functions": [f.to_dict() for f in storage.list_functions(project)]}


@router.get("/projects/{project}/locations/{location}/functions/{name}")
async def get_function(project: str, location: str, name: str) -> Dict[str, Any]:
    fn = storage.get_function(project, name)
    if not fn:
        raise HTTPException(404, f"Function '{name}' not found")
    return fn.to_dict()


@router.delete("/projects/{project}/locations/{location}/functions/{name}")
async def delete_function(project: str, location: str, name: str) -> Dict[str, Any]:
    if not storage.delete_function(project, name):
        raise HTTPException(404, f"Function '{name}' not found")
    return {}


@router.post("/invoke/{project}/{location}/{name}")
async def invoke_function(project: str, location: str, name: str, body: Optional[Dict[str, Any]] = Body(default=None)) -> Any:
    result, status, error = storage.invoke_function(project, location, name, body)
    if status == 404:
        raise HTTPException(404, error)
    if error and result is None:
        return {"error": error}
    return result


@router.get("/functions/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats(), "supportedRuntimes": SUPPORTED_RUNTIMES}
