"""Cloud Identity Platform data models: users and sessions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import hashlib
import secrets
import uuid


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


@dataclass
class IdentityUser:
    project_id: str
    local_id: str
    email: str
    password_salt: str
    password_hash: str
    display_name: str = ""
    disabled: bool = False
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def verify_password(self, password: str) -> bool:
        return hash_password(password, self.password_salt) == self.password_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "localId": self.local_id,
            "email": self.email,
            "displayName": self.display_name,
            "disabled": self.disabled,
            "createdAt": self.create_time.isoformat() + "Z",
        }


@dataclass
class IdentitySession:
    token: str
    project_id: str
    local_id: str
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def new_local_id() -> str:
    return uuid.uuid4().hex


def new_token() -> str:
    return secrets.token_urlsafe(32)


def new_salt() -> str:
    return secrets.token_hex(8)
