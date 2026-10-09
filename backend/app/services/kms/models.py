"""
Cloud KMS data models.

Simulates key rings, crypto keys, and key versions with local
AES-based envelope encryption standing in for real HSM-backed KMS keys.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import base64
import hashlib
import secrets


class CryptoKeyPurpose:
    ENCRYPT_DECRYPT = "ENCRYPT_DECRYPT"
    ASYMMETRIC_SIGN = "ASYMMETRIC_SIGN"
    ASYMMETRIC_DECRYPT = "ASYMMETRIC_DECRYPT"
    MAC = "MAC"


class CryptoKeyVersionState:
    PENDING_GENERATION = "PENDING_GENERATION"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    DESTROYED = "DESTROYED"
    DESTROY_SCHEDULED = "DESTROY_SCHEDULED"


class ProtectionLevel:
    SOFTWARE = "SOFTWARE"
    HSM = "HSM"


@dataclass
class CryptoKeyVersion:
    key_ring_id: str
    crypto_key_id: str
    project_id: str
    location: str
    version_id: str
    state: str = CryptoKeyVersionState.ENABLED
    protection_level: str = ProtectionLevel.SOFTWARE
    algorithm: str = "GOOGLE_SYMMETRIC_ENCRYPTION"
    # The "key material" backing this version. Never returned to clients,
    # mirroring real KMS which never exposes raw key bytes.
    key_material: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    destroy_time: Optional[datetime] = None

    @property
    def name(self) -> str:
        return (
            f"projects/{self.project_id}/locations/{self.location}/"
            f"keyRings/{self.key_ring_id}/cryptoKeys/{self.crypto_key_id}/"
            f"cryptoKeyVersions/{self.version_id}"
        )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "name": self.name,
            "state": self.state,
            "protectionLevel": self.protection_level,
            "algorithm": self.algorithm,
            "createTime": self.create_time.isoformat() + "Z",
        }
        if self.destroy_time:
            data["destroyTime"] = self.destroy_time.isoformat() + "Z"
        return data


@dataclass
class CryptoKey:
    key_ring_id: str
    crypto_key_id: str
    project_id: str
    location: str
    purpose: str = CryptoKeyPurpose.ENCRYPT_DECRYPT
    labels: Dict[str, str] = field(default_factory=dict)
    rotation_period_seconds: Optional[int] = None
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    versions: Dict[str, CryptoKeyVersion] = field(default_factory=dict)
    primary_version_id: Optional[str] = None
    next_version_id: int = 1

    @property
    def name(self) -> str:
        return (
            f"projects/{self.project_id}/locations/{self.location}/"
            f"keyRings/{self.key_ring_id}/cryptoKeys/{self.crypto_key_id}"
        )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "name": self.name,
            "purpose": self.purpose,
            "createTime": self.create_time.isoformat() + "Z",
            "labels": self.labels,
        }
        if self.primary_version_id and self.primary_version_id in self.versions:
            data["primary"] = self.versions[self.primary_version_id].to_dict()
        if self.rotation_period_seconds:
            data["rotationPeriod"] = f"{self.rotation_period_seconds}s"
        return data

    def add_version(self) -> CryptoKeyVersion:
        version_id = str(self.next_version_id)
        self.next_version_id += 1
        version = CryptoKeyVersion(
            key_ring_id=self.key_ring_id,
            crypto_key_id=self.crypto_key_id,
            project_id=self.project_id,
            location=self.location,
            version_id=version_id,
        )
        self.versions[version_id] = version
        if self.primary_version_id is None:
            self.primary_version_id = version_id
        return version

    def primary_key_material(self) -> Optional[bytes]:
        if not self.primary_version_id:
            return None
        version = self.versions.get(self.primary_version_id)
        if not version or version.state != CryptoKeyVersionState.ENABLED:
            return None
        return version.key_material


@dataclass
class KeyRing:
    key_ring_id: str
    project_id: str
    location: str
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    crypto_keys: Dict[str, CryptoKey] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/keyRings/{self.key_ring_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "createTime": self.create_time.isoformat() + "Z",
        }


def xor_crypt(data: bytes, key_material: bytes) -> bytes:
    """Lightweight reversible cipher used to simulate symmetric encrypt/decrypt.

    Not cryptographically meaningful (this is a local emulator, not a real KMS)
    but it is a real, deterministic, reversible transform keyed off the crypto
    key's material, which is what callers actually need to exercise.
    """
    keystream = hashlib.sha256(key_material).digest()
    while len(keystream) < len(data):
        keystream += hashlib.sha256(keystream).digest()
    return bytes(b ^ k for b, k in zip(data, keystream))


def encrypt_with_key(plaintext: bytes, key_material: bytes) -> bytes:
    return xor_crypt(plaintext, key_material)


def decrypt_with_key(ciphertext: bytes, key_material: bytes) -> bytes:
    return xor_crypt(ciphertext, key_material)
