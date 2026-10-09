"""Cloud CDN data models: backend buckets and cached entries."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class BackendBucket:
    project_id: str
    name: str
    bucket_name: str
    cache_ttl_seconds: int = 3600
    enable_cdn: bool = True
    create_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def self_link(self) -> str:
        return f"projects/{self.project_id}/global/backendBuckets/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "selfLink": self.self_link,
            "bucketName": self.bucket_name,
            "cdnPolicy": {"cacheMode": "CACHE_ALL_STATIC", "defaultTtl": self.cache_ttl_seconds},
            "enableCdn": self.enable_cdn,
            "creationTimestamp": self.create_time.isoformat() + "Z",
        }


@dataclass
class CacheEntry:
    content: bytes
    content_type: str
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0

    def is_fresh(self, ttl_seconds: int) -> bool:
        age = (datetime.now(timezone.utc) - self.cached_at).total_seconds()
        return age < ttl_seconds
