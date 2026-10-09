"""
Cloud KMS API endpoints.

Implements a subset of cloudkms.googleapis.com/v1: key rings, crypto keys,
crypto key versions, and symmetric encrypt/decrypt.
"""

from typing import Any, Dict
import base64
import logging

from fastapi import APIRouter, HTTPException, Query

from .storage import storage
from .models import CryptoKeyPurpose, CryptoKeyVersionState, encrypt_with_key, decrypt_with_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project}/locations/{location}/keyRings")
async def create_key_ring(project: str, location: str, key_ring_id: str = Query(..., alias="keyRingId")) -> Dict[str, Any]:
    try:
        ring = storage.create_key_ring(project, location, key_ring_id)
        return ring.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/locations/{location}/keyRings")
async def list_key_rings(project: str, location: str) -> Dict[str, Any]:
    rings = storage.list_key_rings(project, location)
    return {"keyRings": [r.to_dict() for r in rings]}


@router.get("/projects/{project}/locations/{location}/keyRings/{key_ring}")
async def get_key_ring(project: str, location: str, key_ring: str) -> Dict[str, Any]:
    ring = storage.get_key_ring(project, location, key_ring)
    if not ring:
        raise HTTPException(404, f"KeyRing '{key_ring}' not found")
    return ring.to_dict()


@router.post("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys")
async def create_crypto_key(
    project: str, location: str, key_ring: str,
    body: Dict[str, Any], crypto_key_id: str = Query(..., alias="cryptoKeyId"),
) -> Dict[str, Any]:
    purpose = body.get("purpose", CryptoKeyPurpose.ENCRYPT_DECRYPT)
    labels = body.get("labels", {})
    rotation_period = body.get("rotationPeriod")
    rotation_seconds = None
    if isinstance(rotation_period, str) and rotation_period.endswith("s"):
        try:
            rotation_seconds = int(rotation_period[:-1])
        except ValueError:
            rotation_seconds = None
    try:
        key = storage.create_crypto_key(
            project, location, key_ring, crypto_key_id, purpose, labels, rotation_seconds
        )
        return key.to_dict()
    except ValueError as e:
        code = 409 if "already exists" in str(e) else 404
        raise HTTPException(code, str(e))


@router.get("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys")
async def list_crypto_keys(project: str, location: str, key_ring: str) -> Dict[str, Any]:
    keys = storage.list_crypto_keys(project, location, key_ring)
    return {"cryptoKeys": [k.to_dict() for k in keys]}


@router.get("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}")
async def get_crypto_key(project: str, location: str, key_ring: str, crypto_key: str) -> Dict[str, Any]:
    key = storage.get_crypto_key(project, location, key_ring, crypto_key)
    if not key:
        raise HTTPException(404, f"CryptoKey '{crypto_key}' not found")
    return key.to_dict()


@router.post("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}/cryptoKeyVersions")
async def create_crypto_key_version(project: str, location: str, key_ring: str, crypto_key: str) -> Dict[str, Any]:
    try:
        version = storage.create_version(project, location, key_ring, crypto_key)
        return version.to_dict()
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}/cryptoKeyVersions")
async def list_crypto_key_versions(project: str, location: str, key_ring: str, crypto_key: str) -> Dict[str, Any]:
    versions = storage.list_versions(project, location, key_ring, crypto_key)
    return {"cryptoKeyVersions": [v.to_dict() for v in versions]}


@router.get("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}/cryptoKeyVersions/{version}")
async def get_crypto_key_version(project: str, location: str, key_ring: str, crypto_key: str, version: str) -> Dict[str, Any]:
    v = storage.get_version(project, location, key_ring, crypto_key, version)
    if not v:
        raise HTTPException(404, f"CryptoKeyVersion '{version}' not found")
    return v.to_dict()


@router.patch("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}/cryptoKeyVersions/{version}")
async def update_crypto_key_version_state(
    project: str, location: str, key_ring: str, crypto_key: str, version: str, body: Dict[str, Any]
) -> Dict[str, Any]:
    state = body.get("state")
    if state not in (CryptoKeyVersionState.ENABLED, CryptoKeyVersionState.DISABLED):
        raise HTTPException(400, "state must be ENABLED or DISABLED")
    v = storage.set_version_state(project, location, key_ring, crypto_key, version, state)
    if not v:
        raise HTTPException(404, f"CryptoKeyVersion '{version}' not found")
    return v.to_dict()


@router.post("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}/cryptoKeyVersions/{version}:destroy")
async def destroy_crypto_key_version(project: str, location: str, key_ring: str, crypto_key: str, version: str) -> Dict[str, Any]:
    v = storage.destroy_version(project, location, key_ring, crypto_key, version)
    if not v:
        raise HTTPException(404, f"CryptoKeyVersion '{version}' not found")
    return v.to_dict()


@router.post("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}/cryptoKeyVersions/{version}:restore")
async def restore_crypto_key_version(project: str, location: str, key_ring: str, crypto_key: str, version: str) -> Dict[str, Any]:
    v = storage.set_version_state(project, location, key_ring, crypto_key, version, CryptoKeyVersionState.DISABLED)
    if not v:
        raise HTTPException(404, f"CryptoKeyVersion '{version}' not found")
    return v.to_dict()


@router.post("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}:setPrimary")
async def set_primary_version(project: str, location: str, key_ring: str, crypto_key: str, body: Dict[str, Any]) -> Dict[str, Any]:
    version_id = body.get("cryptoKeyVersionId")
    if not version_id:
        raise HTTPException(400, "cryptoKeyVersionId is required")
    try:
        key = storage.set_primary_version(project, location, key_ring, crypto_key, version_id)
        return key.to_dict()
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}:encrypt")
async def encrypt(project: str, location: str, key_ring: str, crypto_key: str, body: Dict[str, Any]) -> Dict[str, Any]:
    key = storage.get_crypto_key(project, location, key_ring, crypto_key)
    if not key:
        raise HTTPException(404, f"CryptoKey '{crypto_key}' not found")
    key_material = key.primary_key_material()
    if not key_material:
        raise HTTPException(400, "CryptoKey has no enabled primary version")
    plaintext_b64 = body.get("plaintext", "")
    try:
        plaintext = base64.b64decode(plaintext_b64)
    except Exception:
        raise HTTPException(400, "plaintext must be base64-encoded")
    ciphertext = encrypt_with_key(plaintext, key_material)
    return {
        "name": key.name,
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "cryptoKeyVersion": key.versions[key.primary_version_id].name,
    }


@router.post("/projects/{project}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}:decrypt")
async def decrypt(project: str, location: str, key_ring: str, crypto_key: str, body: Dict[str, Any]) -> Dict[str, Any]:
    key = storage.get_crypto_key(project, location, key_ring, crypto_key)
    if not key:
        raise HTTPException(404, f"CryptoKey '{crypto_key}' not found")
    key_material = key.primary_key_material()
    if not key_material:
        raise HTTPException(400, "CryptoKey has no enabled primary version")
    ciphertext_b64 = body.get("ciphertext", "")
    try:
        ciphertext = base64.b64decode(ciphertext_b64)
    except Exception:
        raise HTTPException(400, "ciphertext must be base64-encoded")
    plaintext = decrypt_with_key(ciphertext, key_material)
    return {"plaintext": base64.b64encode(plaintext).decode()}


@router.get("/kms/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
