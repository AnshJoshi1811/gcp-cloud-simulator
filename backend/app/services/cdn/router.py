"""
Cloud CDN API endpoints.

Implements a practical subset of compute.googleapis.com/compute/v1
backendBuckets plus a real content-serving endpoint: a cache miss performs a
genuine HTTP fetch from the existing Cloud Storage object endpoint
(storage/v1/b/{bucket}/o/{object}?alt=media) and caches the bytes in memory
for cacheTtlSeconds; a cache hit never touches storage again until the TTL
expires or the entry is invalidated.
"""

from typing import Any, Dict, Optional
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Response, Body

from .storage import storage

logger = logging.getLogger(__name__)
router = APIRouter()

STORAGE_BASE_URL = "http://localhost:8080"


@router.post("/projects/{project}/global/backendBuckets")
async def create_backend_bucket(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    name = body.get("name")
    bucket_name = body.get("bucketName")
    if not name or not bucket_name:
        raise HTTPException(400, "name and bucketName are required")
    cdn_policy = body.get("cdnPolicy", {})
    ttl = cdn_policy.get("defaultTtl", 3600)
    try:
        bb = storage.create_backend_bucket(project, name, bucket_name, ttl)
        return bb.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/global/backendBuckets")
async def list_backend_buckets(project: str) -> Dict[str, Any]:
    return {"items": [b.to_dict() for b in storage.list_backend_buckets(project)]}


@router.get("/projects/{project}/global/backendBuckets/{name}")
async def get_backend_bucket(project: str, name: str) -> Dict[str, Any]:
    bb = storage.get_backend_bucket(project, name)
    if not bb:
        raise HTTPException(404, f"BackendBucket '{name}' not found")
    return bb.to_dict()


@router.delete("/projects/{project}/global/backendBuckets/{name}")
async def delete_backend_bucket(project: str, name: str) -> Dict[str, Any]:
    if not storage.delete_backend_bucket(project, name):
        raise HTTPException(404, f"BackendBucket '{name}' not found")
    return {}


@router.post("/projects/{project}/global/backendBuckets/{name}/invalidateCache")
async def invalidate_cache(project: str, name: str, body: Optional[Dict[str, Any]] = Body(default=None)) -> Dict[str, Any]:
    bb = storage.get_backend_bucket(project, name)
    if not bb:
        raise HTTPException(404, f"BackendBucket '{name}' not found")
    object_path = (body or {}).get("path")
    count = storage.invalidate(bb.bucket_name, object_path.lstrip("/") if object_path else None)
    return {"invalidatedCount": count}


@router.get("/content/{backend_bucket}/{object_path:path}")
async def serve_content(backend_bucket: str, object_path: str) -> Response:
    """Serves object content through the CDN cache for a backend bucket name.

    Path: /cdn/v1/content/{backendBucket}/{objectPath}
    """
    # Need project context to resolve backend bucket -> real bucket name; CDN
    # backend buckets are looked up across all projects by name since the
    # public CDN URL doesn't carry a project segment (matches real GCP CDN
    # URLs, which are also project-agnostic).
    bb = None
    for project_buckets in storage.backend_buckets.values():
        if backend_bucket in project_buckets:
            bb = project_buckets[backend_bucket]
            break
    if not bb:
        raise HTTPException(404, f"BackendBucket '{backend_bucket}' not found")

    cached = storage.get_cached(bb.bucket_name, object_path, bb.cache_ttl_seconds)
    if cached:
        return Response(content=cached.content, media_type=cached.content_type, headers={"X-Cache": "HIT"})

    import requests

    url = f"{STORAGE_BASE_URL}/storage/v1/b/{bb.bucket_name}/o/{object_path}?alt=media"
    try:
        # Run on a worker thread: this is a loopback call into this same
        # server, and uvicorn's single event loop would otherwise deadlock
        # waiting on itself if this blocking call ran inline.
        resp = await asyncio.to_thread(requests.get, url, timeout=10)
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch object from storage: {e}")
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, f"Object '{object_path}' not found in bucket '{bb.bucket_name}'")

    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    storage.put_cached(bb.bucket_name, object_path, resp.content, content_type)
    return Response(content=resp.content, media_type=content_type, headers={"X-Cache": "MISS"})


@router.get("/cdn/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
