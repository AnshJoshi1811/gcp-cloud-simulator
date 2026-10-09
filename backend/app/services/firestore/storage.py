"""In-memory storage for Firestore documents, grouped by project/database/collection."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import threading
import uuid

from .models import Document


class FirestoreStorage:
    def __init__(self):
        self._lock = threading.Lock()
        # project_id -> database_id -> collection_id -> document_id -> Document
        self.data: Dict[str, Dict[str, Dict[str, Dict[str, Document]]]] = {}

    def _collection(self, project_id: str, database_id: str, collection_id: str) -> Dict[str, Document]:
        db = self.data.setdefault(project_id, {}).setdefault(database_id, {})
        return db.setdefault(collection_id, {})

    def create_document(
        self, project_id: str, database_id: str, collection_id: str,
        fields: Dict[str, Any], document_id: Optional[str] = None,
    ) -> Document:
        with self._lock:
            collection = self._collection(project_id, database_id, collection_id)
            doc_id = document_id or uuid.uuid4().hex
            if doc_id in collection:
                raise ValueError(f"Document '{doc_id}' already exists")
            doc = Document(
                project_id=project_id, database_id=database_id,
                collection_id=collection_id, document_id=doc_id, fields=fields,
            )
            collection[doc_id] = doc
            return doc

    def get_document(
        self, project_id: str, database_id: str, collection_id: str, document_id: str
    ) -> Optional[Document]:
        return self._collection(project_id, database_id, collection_id).get(document_id)

    def list_documents(
        self, project_id: str, database_id: str, collection_id: str,
        page_size: int = 100,
    ) -> List[Document]:
        docs = list(self._collection(project_id, database_id, collection_id).values())
        return docs[:page_size]

    def set_document(
        self, project_id: str, database_id: str, collection_id: str,
        document_id: str, fields: Dict[str, Any], merge: bool = False,
    ) -> Document:
        with self._lock:
            collection = self._collection(project_id, database_id, collection_id)
            existing = collection.get(document_id)
            if existing and merge:
                existing.fields.update(fields)
                existing.update_time = datetime.now(timezone.utc)
                return existing
            doc = Document(
                project_id=project_id, database_id=database_id,
                collection_id=collection_id, document_id=document_id, fields=fields,
                create_time=existing.create_time if existing else datetime.now(timezone.utc),
            )
            collection[document_id] = doc
            return doc

    def delete_document(
        self, project_id: str, database_id: str, collection_id: str, document_id: str
    ) -> bool:
        collection = self._collection(project_id, database_id, collection_id)
        with self._lock:
            if document_id in collection:
                del collection[document_id]
                return True
            return False

    def run_query(
        self, project_id: str, database_id: str, collection_id: str,
        field_filters: List[tuple], limit: Optional[int] = None,
    ) -> List[Document]:
        """field_filters: list of (field_path, op, value) tuples. Only '==' is supported."""
        docs = list(self._collection(project_id, database_id, collection_id).values())
        for field_path, op, value in field_filters:
            if op != "EQUAL":
                continue
            docs = [d for d in docs if d.fields.get(field_path) == value]
        if limit is not None:
            docs = docs[:limit]
        return docs

    def list_collections(self, project_id: str, database_id: str) -> List[str]:
        return list(self.data.get(project_id, {}).get(database_id, {}).keys())

    def get_stats(self) -> Dict[str, int]:
        docs = 0
        collections = 0
        for dbs in self.data.values():
            for colls in dbs.values():
                collections += len(colls)
                for c in colls.values():
                    docs += len(c)
        return {"documents": docs, "collections": collections}


storage = FirestoreStorage()
