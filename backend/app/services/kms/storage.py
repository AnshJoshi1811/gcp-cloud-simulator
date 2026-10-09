"""In-memory storage for Cloud KMS key rings, crypto keys, and versions."""

from typing import Dict, List, Optional
import threading

from .models import KeyRing, CryptoKey, CryptoKeyVersion, CryptoKeyVersionState
from datetime import datetime, timezone


class KMSStorage:
    def __init__(self):
        self._lock = threading.Lock()
        # (project_id, location) -> key_ring_id -> KeyRing
        self.key_rings: Dict[str, Dict[str, KeyRing]] = {}

    def _scope(self, project_id: str, location: str) -> str:
        return f"{project_id}/{location}"

    def create_key_ring(self, project_id: str, location: str, key_ring_id: str) -> KeyRing:
        with self._lock:
            scope = self._scope(project_id, location)
            rings = self.key_rings.setdefault(scope, {})
            if key_ring_id in rings:
                raise ValueError(f"KeyRing '{key_ring_id}' already exists")
            ring = KeyRing(key_ring_id=key_ring_id, project_id=project_id, location=location)
            rings[key_ring_id] = ring
            return ring

    def get_key_ring(self, project_id: str, location: str, key_ring_id: str) -> Optional[KeyRing]:
        return self.key_rings.get(self._scope(project_id, location), {}).get(key_ring_id)

    def list_key_rings(self, project_id: str, location: str) -> List[KeyRing]:
        return list(self.key_rings.get(self._scope(project_id, location), {}).values())

    def create_crypto_key(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str,
        purpose: str, labels: Optional[Dict[str, str]] = None,
        rotation_period_seconds: Optional[int] = None,
    ) -> CryptoKey:
        ring = self.get_key_ring(project_id, location, key_ring_id)
        if not ring:
            raise ValueError(f"KeyRing '{key_ring_id}' not found")
        with self._lock:
            if crypto_key_id in ring.crypto_keys:
                raise ValueError(f"CryptoKey '{crypto_key_id}' already exists")
            key = CryptoKey(
                key_ring_id=key_ring_id,
                crypto_key_id=crypto_key_id,
                project_id=project_id,
                location=location,
                purpose=purpose,
                labels=labels or {},
                rotation_period_seconds=rotation_period_seconds,
            )
            key.add_version()
            ring.crypto_keys[crypto_key_id] = key
            return key

    def get_crypto_key(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str
    ) -> Optional[CryptoKey]:
        ring = self.get_key_ring(project_id, location, key_ring_id)
        if not ring:
            return None
        return ring.crypto_keys.get(crypto_key_id)

    def list_crypto_keys(self, project_id: str, location: str, key_ring_id: str) -> List[CryptoKey]:
        ring = self.get_key_ring(project_id, location, key_ring_id)
        if not ring:
            return []
        return list(ring.crypto_keys.values())

    def create_version(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str
    ) -> CryptoKeyVersion:
        key = self.get_crypto_key(project_id, location, key_ring_id, crypto_key_id)
        if not key:
            raise ValueError(f"CryptoKey '{crypto_key_id}' not found")
        with self._lock:
            return key.add_version()

    def get_version(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str, version_id: str
    ) -> Optional[CryptoKeyVersion]:
        key = self.get_crypto_key(project_id, location, key_ring_id, crypto_key_id)
        if not key:
            return None
        return key.versions.get(version_id)

    def list_versions(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str
    ) -> List[CryptoKeyVersion]:
        key = self.get_crypto_key(project_id, location, key_ring_id, crypto_key_id)
        if not key:
            return []
        return list(key.versions.values())

    def set_primary_version(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str, version_id: str
    ) -> CryptoKey:
        key = self.get_crypto_key(project_id, location, key_ring_id, crypto_key_id)
        if not key:
            raise ValueError(f"CryptoKey '{crypto_key_id}' not found")
        if version_id not in key.versions:
            raise ValueError(f"CryptoKeyVersion '{version_id}' not found")
        with self._lock:
            key.primary_version_id = version_id
            return key

    def destroy_version(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str, version_id: str
    ) -> Optional[CryptoKeyVersion]:
        version = self.get_version(project_id, location, key_ring_id, crypto_key_id, version_id)
        if not version:
            return None
        with self._lock:
            version.state = CryptoKeyVersionState.DESTROYED
            version.destroy_time = datetime.now(timezone.utc)
            return version

    def set_version_state(
        self, project_id: str, location: str, key_ring_id: str, crypto_key_id: str,
        version_id: str, state: str,
    ) -> Optional[CryptoKeyVersion]:
        version = self.get_version(project_id, location, key_ring_id, crypto_key_id, version_id)
        if not version:
            return None
        with self._lock:
            version.state = state
            return version

    def get_stats(self) -> Dict[str, int]:
        total_rings = sum(len(r) for r in self.key_rings.values())
        total_keys = sum(len(ring.crypto_keys) for rings in self.key_rings.values() for ring in rings.values())
        return {"keyRings": total_rings, "cryptoKeys": total_keys}


storage = KMSStorage()
