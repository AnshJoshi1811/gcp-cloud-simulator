"""
Cloud Identity Platform API endpoints.

Implements a practical subset of identitytoolkit.googleapis.com/v1 (Firebase
Auth-shaped: signUp / signInWithPassword / lookup), scoped per GCP project,
plus a GCP-admin-style user list/delete under identitytoolkit's accounts
resource. Passwords are salted-hashed (not reversible), never returned.
"""

from typing import Any, Dict
import logging

from fastapi import APIRouter, HTTPException

from .storage import storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project}/accounts:signUp")
async def sign_up(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        raise HTTPException(400, "email and password are required")
    try:
        user = storage.sign_up(project, email, password, body.get("displayName", ""))
    except ValueError as e:
        raise HTTPException(409, str(e))
    session = storage.create_session(user)
    return {"localId": user.local_id, "email": user.email, "idToken": session.token}


@router.post("/projects/{project}/accounts:signInWithPassword")
async def sign_in(project: str, body: Dict[str, Any]) -> Dict[str, Any]:
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        raise HTTPException(400, "email and password are required")
    try:
        user = storage.sign_in(project, email, password)
    except ValueError as e:
        raise HTTPException(401, str(e))
    session = storage.create_session(user)
    return {"localId": user.local_id, "email": user.email, "idToken": session.token}


@router.post("/accounts:lookup")
async def lookup(body: Dict[str, Any]) -> Dict[str, Any]:
    id_token = body.get("idToken")
    if not id_token:
        raise HTTPException(400, "idToken is required")
    user = storage.get_user_by_token(id_token)
    if not user:
        raise HTTPException(401, "Invalid or expired idToken")
    return {"users": [user.to_dict()]}


@router.get("/projects/{project}/accounts")
async def list_users(project: str) -> Dict[str, Any]:
    return {"users": [u.to_dict() for u in storage.list_users(project)]}


@router.get("/projects/{project}/accounts/{local_id}")
async def get_user(project: str, local_id: str) -> Dict[str, Any]:
    user = storage.get_user(project, local_id)
    if not user:
        raise HTTPException(404, f"User '{local_id}' not found")
    return user.to_dict()


@router.delete("/projects/{project}/accounts/{local_id}")
async def delete_user(project: str, local_id: str) -> Dict[str, Any]:
    if not storage.delete_user(project, local_id):
        raise HTTPException(404, f"User '{local_id}' not found")
    return {}


@router.post("/projects/{project}/accounts/{local_id}:disable")
async def disable_user(project: str, local_id: str) -> Dict[str, Any]:
    user = storage.set_disabled(project, local_id, True)
    if not user:
        raise HTTPException(404, f"User '{local_id}' not found")
    return user.to_dict()


@router.post("/projects/{project}/accounts/{local_id}:enable")
async def enable_user(project: str, local_id: str) -> Dict[str, Any]:
    user = storage.set_disabled(project, local_id, False)
    if not user:
        raise HTTPException(404, f"User '{local_id}' not found")
    return user.to_dict()


@router.get("/identity/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
