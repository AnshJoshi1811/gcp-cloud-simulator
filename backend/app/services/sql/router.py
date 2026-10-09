"""
Cloud SQL Admin API endpoints.

Implements a subset of sqladmin.googleapis.com/v1: instances, databases, users.
Each instance is backed by a real postgres/mysql Docker container (falls back
to a stub record if Docker is unavailable, matching docker_manager.py's
existing stub-mode philosophy).
"""

from typing import Any, Dict
import logging

from fastapi import APIRouter, HTTPException

from .storage import storage
from .models import DatabaseVersion

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project}/instances")
async def create_instance(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    instance_id = body.get("name")
    if not instance_id:
        raise HTTPException(400, "name is required")
    region = body.get("region", "us-central1")
    database_version = body.get("databaseVersion", DatabaseVersion.POSTGRES_15)
    if database_version not in (DatabaseVersion.POSTGRES_15, DatabaseVersion.MYSQL_8_0):
        raise HTTPException(
            400,
            f"Unsupported databaseVersion '{database_version}'. "
            f"Supported: {DatabaseVersion.POSTGRES_15}, {DatabaseVersion.MYSQL_8_0}",
        )
    settings = body.get("settings", {})
    tier = settings.get("tier", "db-f1-micro")
    root_password = body.get("rootPassword")
    labels = settings.get("userLabels", {})

    try:
        instance = storage.create_instance(
            project, instance_id, region, database_version, tier, root_password, labels
        )
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/instances")
async def list_instances(project: str) -> Dict[str, Any]:
    instances = storage.list_instances(project)
    return {"kind": "sql#instancesList", "items": [i.to_dict() for i in instances]}


@router.get("/projects/{project}/instances/{instance}")
async def get_instance(project: str, instance: str) -> Dict[str, Any]:
    inst = storage.get_instance(project, instance)
    if not inst:
        raise HTTPException(404, f"Instance '{instance}' not found")
    return inst.to_dict()


@router.delete("/projects/{project}/instances/{instance}")
async def delete_instance(project: str, instance: str) -> Dict[str, Any]:
    if not storage.delete_instance(project, instance):
        raise HTTPException(404, f"Instance '{instance}' not found")
    return {"kind": "sql#operation", "status": "DONE", "operationType": "DELETE"}


@router.post("/projects/{project}/instances/{instance}:stop")
async def stop_instance(project: str, instance: str) -> Dict[str, Any]:
    inst = storage.stop_instance(project, instance)
    if not inst:
        raise HTTPException(404, f"Instance '{instance}' not found")
    return inst.to_dict()


@router.post("/projects/{project}/instances/{instance}:start")
async def start_instance(project: str, instance: str) -> Dict[str, Any]:
    inst = storage.start_instance(project, instance)
    if not inst:
        raise HTTPException(404, f"Instance '{instance}' not found")
    return inst.to_dict()


@router.post("/projects/{project}/instances/{instance}/databases")
async def create_database(project: str, instance: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    if not name:
        raise HTTPException(400, "name is required")
    try:
        db = storage.create_database(project, instance, name)
        return db.to_dict()
    except ValueError as e:
        code = 409 if "already exists" in str(e) else 404
        raise HTTPException(code, str(e))


@router.get("/projects/{project}/instances/{instance}/databases")
async def list_databases(project: str, instance: str) -> Dict[str, Any]:
    dbs = storage.list_databases(project, instance)
    return {"kind": "sql#databasesList", "items": [d.to_dict() for d in dbs]}


@router.delete("/projects/{project}/instances/{instance}/databases/{database}")
async def delete_database(project: str, instance: str, database: str) -> Dict[str, Any]:
    if not storage.delete_database(project, instance, database):
        raise HTTPException(404, f"Database '{database}' not found")
    return {"kind": "sql#operation", "status": "DONE", "operationType": "DELETE_DATABASE"}


@router.post("/projects/{project}/instances/{instance}/users")
async def create_user(project: str, instance: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    if not name:
        raise HTTPException(400, "name is required")
    try:
        user = storage.create_user(project, instance, name, body.get("password"))
        data = user.to_dict()
        data["password"] = user.password  # only returned at creation time, like real GCP
        return data
    except ValueError as e:
        code = 409 if "already exists" in str(e) else 404
        raise HTTPException(code, str(e))


@router.get("/projects/{project}/instances/{instance}/users")
async def list_users(project: str, instance: str) -> Dict[str, Any]:
    users = storage.list_users(project, instance)
    return {"kind": "sql#usersList", "items": [u.to_dict() for u in users]}


@router.get("/sql/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
