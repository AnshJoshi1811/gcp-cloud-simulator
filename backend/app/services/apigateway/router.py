"""
API Gateway API endpoints.

Implements a practical subset of apigateway.googleapis.com/v1: API configs
(a list of path/method -> backend routes), gateways, and a real proxy
endpoint that resolves an incoming request's path through the gateway's
routes and forwards it — to a deployed Cloud Function (invoked in-process via
the functions service) or to an arbitrary backend URL.
"""

from typing import Any, Dict, Optional
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request

from .storage import storage
from .models import Route
from app.services.functions.storage import storage as functions_storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project}/apis/{api_id}/configs")
async def create_config(project: str, api_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    config_id = body.get("configId")
    if not config_id:
        raise HTTPException(400, "configId is required")
    routes = [
        Route(
            path=r.get("path"),
            method=r.get("method", "ANY"),
            backend_function=r.get("backendFunction"),
            backend_url=r.get("backendUrl"),
        )
        for r in body.get("routes", [])
    ]
    for r in routes:
        if not r.path:
            raise HTTPException(400, "each route requires a path")
        if not r.backend_function and not r.backend_url:
            raise HTTPException(400, f"route '{r.path}' requires backendFunction or backendUrl")
    try:
        config = storage.create_config(project, api_id, config_id, routes)
        return config.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/apis/{api_id}/configs")
async def list_configs(project: str, api_id: str) -> Dict[str, Any]:
    configs = [c for c in storage.list_configs(project) if c.api_id == api_id]
    return {"apiConfigs": [c.to_dict() for c in configs]}


@router.post("/projects/{project}/locations/{location}/gateways")
async def create_gateway(project: str, location: str, body: Dict[str, Any]) -> Dict[str, Any]:
    gateway_id = body.get("gatewayId")
    api_config = body.get("apiConfig")
    if not gateway_id or not api_config:
        raise HTTPException(400, "gatewayId and apiConfig are required")
    try:
        gw = storage.create_gateway(project, location, gateway_id, api_config)
        return gw.to_dict()
    except ValueError as e:
        code = 409 if "already exists" in str(e) else 404
        raise HTTPException(code, str(e))


@router.get("/projects/{project}/locations/{location}/gateways")
async def list_gateways(project: str, location: str) -> Dict[str, Any]:
    return {"gateways": [g.to_dict() for g in storage.list_gateways(project)]}


@router.get("/projects/{project}/locations/{location}/gateways/{gateway_id}")
async def get_gateway(project: str, location: str, gateway_id: str) -> Dict[str, Any]:
    gw = storage.get_gateway(project, gateway_id)
    if not gw:
        raise HTTPException(404, f"Gateway '{gateway_id}' not found")
    return gw.to_dict()


@router.delete("/projects/{project}/locations/{location}/gateways/{gateway_id}")
async def delete_gateway(project: str, location: str, gateway_id: str) -> Dict[str, Any]:
    if not storage.delete_gateway(project, gateway_id):
        raise HTTPException(404, f"Gateway '{gateway_id}' not found")
    return {}


@router.api_route("/invoke/{project}/{gateway_id}/{proxy_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(project: str, gateway_id: str, proxy_path: str, request: Request) -> Any:
    path = "/" + proxy_path
    gw, route = storage.find_route(project, gateway_id, path, request.method)
    if not gw:
        raise HTTPException(404, f"Gateway '{gateway_id}' not found")
    if not route:
        raise HTTPException(404, f"No route matches '{path}' [{request.method}] on gateway '{gateway_id}'")

    body: Optional[Dict[str, Any]] = None
    try:
        body = await request.json()
    except Exception:
        body = None

    if route.backend_function:
        result, status, error = functions_storage.invoke_function(
            project, gw.location, route.backend_function, body
        )
        if status == 404:
            raise HTTPException(404, error)
        return result if not error else {"error": error}

    if route.backend_url:
        import requests

        try:
            # Run on a worker thread: backend_url can point back at this same
            # server, and uvicorn's single event loop would deadlock waiting
            # on itself if this blocking call ran inline.
            resp = await asyncio.to_thread(
                requests.request, request.method, route.backend_url, json=body, timeout=10
            )
            try:
                return resp.json()
            except ValueError:
                return resp.text
        except Exception as e:
            raise HTTPException(502, f"Backend request failed: {e}")

    raise HTTPException(500, "route has no backend configured")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
