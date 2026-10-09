"""In-memory storage for Cloud Identity Platform users and sessions."""

from typing import Dict, List, Optional
import threading

from .models import IdentityUser, IdentitySession, hash_password, new_local_id, new_token, new_salt


class IdentityStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.users: Dict[str, Dict[str, IdentityUser]] = {}  # project_id -> local_id -> user
        self.sessions: Dict[str, IdentitySession] = {}  # token -> session

    def _by_email(self, project_id: str, email: str) -> Optional[IdentityUser]:
        for user in self.users.get(project_id, {}).values():
            if user.email == email:
                return user
        return None

    def sign_up(self, project_id: str, email: str, password: str, display_name: str = "") -> IdentityUser:
        with self._lock:
            if self._by_email(project_id, email):
                raise ValueError(f"Email '{email}' is already registered")
            salt = new_salt()
            user = IdentityUser(
                project_id=project_id, local_id=new_local_id(), email=email,
                password_salt=salt, password_hash=hash_password(password, salt),
                display_name=display_name,
            )
            self.users.setdefault(project_id, {})[user.local_id] = user
            return user

    def sign_in(self, project_id: str, email: str, password: str) -> IdentityUser:
        user = self._by_email(project_id, email)
        if not user or not user.verify_password(password):
            raise ValueError("Invalid email or password")
        if user.disabled:
            raise ValueError("User account is disabled")
        return user

    def create_session(self, user: IdentityUser) -> IdentitySession:
        session = IdentitySession(token=new_token(), project_id=user.project_id, local_id=user.local_id)
        with self._lock:
            self.sessions[session.token] = session
        return session

    def get_user_by_token(self, token: str) -> Optional[IdentityUser]:
        session = self.sessions.get(token)
        if not session:
            return None
        return self.users.get(session.project_id, {}).get(session.local_id)

    def get_user(self, project_id: str, local_id: str) -> Optional[IdentityUser]:
        return self.users.get(project_id, {}).get(local_id)

    def list_users(self, project_id: str) -> List[IdentityUser]:
        return list(self.users.get(project_id, {}).values())

    def delete_user(self, project_id: str, local_id: str) -> bool:
        with self._lock:
            if local_id in self.users.get(project_id, {}):
                del self.users[project_id][local_id]
                return True
            return False

    def set_disabled(self, project_id: str, local_id: str, disabled: bool) -> Optional[IdentityUser]:
        user = self.get_user(project_id, local_id)
        if user:
            user.disabled = disabled
        return user

    def get_stats(self) -> Dict[str, int]:
        return {"users": sum(len(u) for u in self.users.values()), "sessions": len(self.sessions)}


storage = IdentityStorage()
