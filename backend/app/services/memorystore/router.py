"""
Memorystore API endpoints.

Implements a subset of redis.googleapis.com/v1: Redis instances backed by a
real redis:7-alpine Docker container (falls back to a stub when Docker is
unavailable).
"""

from typing import Any, Dict
import logging

from fastapi import APIRouter, HTTPException

from .storage import storage
from .models import InstanceTier

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project}/locations/{location}/instances")
async def create_instance(project: str, location: str, body: Dict[str, Any]) -> Dict[str, Any]:
    instance_id = body.get("instanceId") or body.get("name")
    if not instance_id:
        raise HTTPException(400, "instanceId is required")
    tier = body.get("tier", InstanceTier.BASIC)
    if tier not in (InstanceTier.BASIC, InstanceTier.STANDARD_HA):
        raise HTTPException(400, f"Unsupported tier '{tier}'. Supported: BASIC, STANDARD_HA")
    memory_size_gb = body.get("memorySizeGb", 1)
    labels = body.get("labels", {})
    try:
        instance = storage.create_instance(project, instance_id, location, tier, memory_size_gb, labels)
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/locations/{location}/instances")
async def list_instances(project: str, location: str) -> Dict[str, Any]:
    instances = storage.list_instances(project)
    return {"instances": [i.to_dict() for i in instances]}


@router.get("/projects/{project}/locations/{location}/instances/{instance}")
async def get_instance(project: str, location: str, instance: str) -> Dict[str, Any]:
    inst = storage.get_instance(project, instance)
    if not inst:
        raise HTTPException(404, f"Instance '{instance}' not found")
    return inst.to_dict()


@router.delete("/projects/{project}/locations/{location}/instances/{instance}")
async def delete_instance(project: str, location: str, instance: str) -> Dict[str, Any]:
    if not storage.delete_instance(project, instance):
        raise HTTPException(404, f"Instance '{instance}' not found")
    return {"done": True}


@router.get("/memorystore/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
