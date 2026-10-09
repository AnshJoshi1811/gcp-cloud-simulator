"""
Firestore API endpoints.

Implements a subset of firestore.googleapis.com/v1: document CRUD and a
simple structured query (equality filters only), using the typed-value wire
format real Firestore clients expect.
"""

from typing import Any, Dict
import logging

from fastapi import APIRouter, HTTPException, Query

from .storage import storage
from .models import encode_fields, decode_fields

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_DATABASE = "(default)"


@router.post("/projects/{project}/databases/{database}/documents/{collection_id}")
async def create_document(
    project: str, database: str, collection_id: str, body: Dict[str, Any],
    document_id: str = Query(None, alias="documentId"),
) -> Dict[str, Any]:
    fields = decode_fields(body.get("fields", {}))
    try:
        doc = storage.create_document(project, database, collection_id, fields, document_id)
        return doc.to_dict()
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/projects/{project}/databases/{database}/documents/{collection_id}")
async def list_documents(
    project: str, database: str, collection_id: str, page_size: int = Query(100, alias="pageSize")
) -> Dict[str, Any]:
    docs = storage.list_documents(project, database, collection_id, page_size)
    return {"documents": [d.to_dict() for d in docs], "nextPageToken": None}


@router.get("/projects/{project}/databases/{database}/documents/{collection_id}/{document_id}")
async def get_document(project: str, database: str, collection_id: str, document_id: str) -> Dict[str, Any]:
    doc = storage.get_document(project, database, collection_id, document_id)
    if not doc:
        raise HTTPException(404, f"Document '{document_id}' not found")
    return doc.to_dict()


@router.patch("/projects/{project}/databases/{database}/documents/{collection_id}/{document_id}")
async def set_document(
    project: str, database: str, collection_id: str, document_id: str, body: Dict[str, Any],
    update_mask: str = Query(None, alias="updateMask.fieldPaths"),
) -> Dict[str, Any]:
    fields = decode_fields(body.get("fields", {}))
    merge = update_mask is not None
    doc = storage.set_document(project, database, collection_id, document_id, fields, merge=merge)
    return doc.to_dict()


@router.delete("/projects/{project}/databases/{database}/documents/{collection_id}/{document_id}")
async def delete_document(project: str, database: str, collection_id: str, document_id: str) -> Dict[str, Any]:
    if not storage.delete_document(project, database, collection_id, document_id):
        raise HTTPException(404, f"Document '{document_id}' not found")
    return {}


@router.post("/projects/{project}/databases/{database}/documents:runQuery")
async def run_query(project: str, database: str, body: Dict[str, Any]) -> Any:
    structured_query = body.get("structuredQuery", {})
    from_clauses = structured_query.get("from", [])
    if not from_clauses:
        raise HTTPException(400, "structuredQuery.from is required")
    collection_id = from_clauses[0].get("collectionId")

    field_filters = []
    where = structured_query.get("where", {})
    field_filter = where.get("fieldFilter")
    if field_filter:
        field_path = field_filter.get("field", {}).get("fieldPath")
        op = field_filter.get("op")
        value = decode_fields({"v": field_filter.get("value", {})})["v"]
        field_filters.append((field_path, op, value))

    limit = structured_query.get("limit")
    docs = storage.run_query(project, database, collection_id, field_filters, limit)
    return [{"document": d.to_dict()} for d in docs]


@router.get("/firestore/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "stats": storage.get_stats()}
