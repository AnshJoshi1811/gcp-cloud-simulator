"""
Firestore data models.

Documents are stored as plain Python dicts internally, and converted to/from
the GCP Firestore REST "typed value" wire format
(https://cloud.google.com/firestore/docs/reference/rest/v1/Value) at the API
boundary, so storage/query logic can stay simple.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class Document:
    project_id: str
    database_id: str
    collection_id: str
    document_id: str
    fields: Dict[str, Any] = field(default_factory=dict)
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    update_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return (
            f"projects/{self.project_id}/databases/{self.database_id}/documents/"
            f"{self.collection_id}/{self.document_id}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fields": encode_fields(self.fields),
            "createTime": self.create_time.isoformat() + "Z",
            "updateTime": self.update_time.isoformat() + "Z",
        }


def _encode_value(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, dict):
        return {"mapValue": {"fields": encode_fields(value)}}
    if isinstance(value, list):
        return {"arrayValue": {"values": [_encode_value(v) for v in value]}}
    return {"stringValue": str(value)}


def encode_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _encode_value(v) for k, v in fields.items()}


def _decode_value(value: Dict[str, Any]) -> Any:
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "stringValue" in value:
        return value["stringValue"]
    if "timestampValue" in value:
        return value["timestampValue"]
    if "mapValue" in value:
        return decode_fields(value["mapValue"].get("fields", {}))
    if "arrayValue" in value:
        return [_decode_value(v) for v in value["arrayValue"].get("values", [])]
    return None


def decode_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _decode_value(v) for k, v in (fields or {}).items()}
