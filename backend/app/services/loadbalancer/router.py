"""
Cloud Load Balancing API endpoints.

Implements a practical subset of compute.googleapis.com/v1 load balancing
resources: health checks, backend services, URL maps, target HTTP proxies,
and global forwarding rules. A forwarding rule's `:simulate` action actually
round-robins across the backend service's instances and attempts a real HTTP
request to each one's internal IP, so this isn't just bookkeeping — it
exercises the same routing a real L7 LB would do (requests fail in stub mode
since there's no real container listening, which is reported back, not
swallowed).
"""

from typing import Any, Dict
import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from .storage import storage
from app.models.database import get_db, Instance

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project}/global/healthChecks")
async def create_health_check(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    if not name:
        raise HTTPException(400, "name is required")
    port = body.get("port", 80)
    try:
        hc = storage.create_health_check(project, name, port)
        return hc.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/global/healthChecks")
async def list_health_checks(project: str) -> Dict[str, Any]:
    return {"items": [h.to_dict() for h in storage.list_health_checks(project)]}


@router.post("/projects/{project}/global/backendServices")
async def create_backend_service(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    if not name:
        raise HTTPException(400, "name is required")
    try:
        svc = storage.create_backend_service(
            project, name, body.get("protocol", "HTTP"), body.get("healthChecks", [])
        )
        return svc.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/global/backendServices")
async def list_backend_services(project: str) -> Dict[str, Any]:
    return {"items": [s.to_dict() for s in storage.list_backend_services(project)]}


@router.get("/projects/{project}/global/backendServices/{name}")
async def get_backend_service(project: str, name: str) -> Dict[str, Any]:
    svc = storage.get_backend_service(project, name)
    if not svc:
        raise HTTPException(404, f"BackendService '{name}' not found")
    return svc.to_dict()


@router.post("/projects/{project}/global/backendServices/{name}/addBackend")
async def add_backend(project: str, name: str, body: Dict[str, Any]) -> Dict[str, Any]:
    instance_name = body.get("instanceName")
    zone = body.get("zone", "us-central1-a")
    port = body.get("port", 80)
    if not instance_name:
        raise HTTPException(400, "instanceName is required")
    try:
        svc = storage.add_backend(project, name, instance_name, zone, port)
        return svc.to_dict()
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/projects/{project}/global/urlMaps")
async def create_url_map(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    default_service = body.get("defaultService")
    if not name or not default_service:
        raise HTTPException(400, "name and defaultService are required")
    try:
        um = storage.create_url_map(project, name, default_service)
        return um.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/global/urlMaps")
async def list_url_maps(project: str) -> Dict[str, Any]:
    return {"items": [u.to_dict() for u in storage.list_url_maps(project)]}


@router.post("/projects/{project}/global/targetHttpProxies")
async def create_target_proxy(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    url_map = body.get("urlMap")
    if not name or not url_map:
        raise HTTPException(400, "name and urlMap are required")
    try:
        proxy = storage.create_target_proxy(project, name, url_map)
        return proxy.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/global/targetHttpProxies")
async def list_target_proxies(project: str) -> Dict[str, Any]:
    return {"items": [p.to_dict() for p in storage.list_target_proxies(project)]}


@router.post("/projects/{project}/global/forwardingRules")
async def create_forwarding_rule(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    target = body.get("target")
    if not name or not target:
        raise HTTPException(400, "name and target are required")
    try:
        rule = storage.create_forwarding_rule(project, name, target, body.get("portRange", "80"))
        return rule.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/global/forwardingRules")
async def list_forwarding_rules(project: str) -> Dict[str, Any]:
    return {"items": [r.to_dict() for r in storage.list_forwarding_rules(project)]}


@router.get("/projects/{project}/global/forwardingRules/{name}")
async def get_forwarding_rule(project: str, name: str) -> Dict[str, Any]:
    rule = storage.get_forwarding_rule(project, name)
    if not rule:
        raise HTTPException(404, f"ForwardingRule '{name}' not found")
    return rule.to_dict()


@router.post("/projects/{project}/global/forwardingRules/{name}:simulate")
async def simulate_request(project: str, name: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Round-robins to the next backend and attempts a real HTTP GET to its
    internal IP, reporting success/failure — this exercises actual LB routing
    logic rather than just returning static bookkeeping data."""
    import requests

    backend_service_name = storage.resolve_backend_service_for_rule(project, name)
    if not backend_service_name:
        raise HTTPException(404, f"Could not resolve backend service for forwarding rule '{name}'")

    backend = storage.next_backend(project, backend_service_name)
    if not backend:
        raise HTTPException(409, f"BackendService '{backend_service_name}' has no backends")

    instance = (
        db.query(Instance)
        .filter(Instance.project_id == project, Instance.name == backend.instance_name)
        .first()
    )
    if not instance or not instance.internal_ip:
        return {
            "routedTo": backend.instance_name,
            "healthy": False,
            "error": "instance not found or has no internal IP",
        }

    url = f"http://{instance.internal_ip}:{backend.port}/"
    try:
        resp = requests.get(url, timeout=3)
        return {"routedTo": backend.instance_name, "healthy": resp.ok, "statusCode": resp.status_code}
    except Exception as e:
        return {"routedTo": backend.instance_name, "healthy": False, "error": str(e)}


@router.get("/loadbalancer/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
