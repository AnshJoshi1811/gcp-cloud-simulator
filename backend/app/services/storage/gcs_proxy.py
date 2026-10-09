"""Real GCS wire-protocol proxy, backed by fake-gcs-server (fsouza/fake-gcs-server).

Why this exists: `backend/app/api/storage.py` hand-rolls GCS's JSON API,
which is enough to satisfy `gcloud` CLI calls but was never verified against
the exact request/response shapes the real `hashicorp/google` Terraform
provider expects. fake-gcs-server is a mature, widely-used emulator that
speaks GCS's actual wire protocol, so proxying the core bucket/object CRUD
paths to it gives genuine protocol fidelity with zero reimplementation risk
— see DECISIONS.md's "Terraform / google-provider compatibility" section
for the full reasoning and the empirical probe that proved this approach
viable.

Only the resource paths a Terraform `google_storage_bucket` /
`google_storage_bucket_object` cycle actually needs are proxied here.
Everything else this repo's Storage service already does (the UI dashboard
stats endpoint, signed URLs, ACLs, rewrite) is NOT duplicated here and keeps
being served by the existing `backend/app/api/storage.py` handlers — this
router is registered before that one in `main.py` so these specific
path+method combinations are intercepted first, and anything not defined
here simply falls through to the existing implementation unchanged.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response

from app.core.docker_manager import ensure_fake_gcs_server

logger = logging.getLogger("gcs_proxy")

router = APIRouter()

_HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length", "host",
}


def _backend_base_url() -> str:
    info = ensure_fake_gcs_server()
    return info["endpoint"]


async def _proxy(request: Request, backend_path: str) -> Response:
    base_url = _backend_base_url()
    if base_url.startswith("stub-") or "stub" in base_url:
        # Docker unavailable: fake-gcs-server can't actually run. Return a
        # clear GCS-style error rather than crashing or silently no-op'ing.
        return Response(
            content=b'{"error": {"code": 503, "message": "Storage backend (fake-gcs-server) unavailable: Docker is not reachable in this environment."}}',
            status_code=503,
            media_type="application/json",
        )

    url = f"{base_url}{backend_path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS}
    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream = await client.request(
            request.method,
            url,
            params=request.query_params,
            headers=headers,
            content=body,
        )

    response_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


@router.get("/storage/v1/b")
async def list_buckets(request: Request):
    return await _proxy(request, "/storage/v1/b")


@router.post("/storage/v1/b")
async def insert_bucket(request: Request):
    return await _proxy(request, "/storage/v1/b")


@router.get("/storage/v1/b/{bucket}")
async def get_bucket(request: Request, bucket: str):
    return await _proxy(request, f"/storage/v1/b/{bucket}")


@router.patch("/storage/v1/b/{bucket}")
async def patch_bucket(request: Request, bucket: str):
    return await _proxy(request, f"/storage/v1/b/{bucket}")


@router.delete("/storage/v1/b/{bucket}", status_code=204)
async def delete_bucket(request: Request, bucket: str):
    return await _proxy(request, f"/storage/v1/b/{bucket}")


@router.get("/storage/v1/b/{bucket}/o")
async def list_objects(request: Request, bucket: str):
    return await _proxy(request, f"/storage/v1/b/{bucket}/o")


@router.get("/storage/v1/b/{bucket}/o/{object_name:path}")
async def get_object(request: Request, bucket: str, object_name: str):
    return await _proxy(request, f"/storage/v1/b/{bucket}/o/{object_name}")


@router.delete("/storage/v1/b/{bucket}/o/{object_name:path}", status_code=204)
async def delete_object(request: Request, bucket: str, object_name: str):
    return await _proxy(request, f"/storage/v1/b/{bucket}/o/{object_name}")


@router.post("/upload/storage/v1/b/{bucket}/o")
async def upload_object(request: Request, bucket: str):
    return await _proxy(request, f"/upload/storage/v1/b/{bucket}/o")


@router.get("/download/storage/v1/b/{bucket}/o/{object_name:path}")
async def download_object(request: Request, bucket: str, object_name: str):
    return await _proxy(request, f"/download/storage/v1/b/{bucket}/o/{object_name}")
