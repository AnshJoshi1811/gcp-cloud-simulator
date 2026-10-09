"""In-memory storage for Cloud CDN backend buckets and cached object content."""

from typing import Dict, List, Optional, Tuple
import threading

from .models import BackendBucket, CacheEntry


class CdnStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.backend_buckets: Dict[str, Dict[str, BackendBucket]] = {}  # project_id -> name -> BackendBucket
        self.cache: Dict[str, CacheEntry] = {}  # f"{bucket}/{object}" -> CacheEntry
        self.hits = 0
        self.misses = 0

    def create_backend_bucket(
        self, project_id: str, name: str, bucket_name: str, cache_ttl_seconds: int = 3600
    ) -> BackendBucket:
        with self._lock:
            bucket = self.backend_buckets.setdefault(project_id, {})
            if name in bucket:
                raise ValueError(f"BackendBucket '{name}' already exists")
            bb = BackendBucket(project_id=project_id, name=name, bucket_name=bucket_name, cache_ttl_seconds=cache_ttl_seconds)
            bucket[name] = bb
            return bb

    def get_backend_bucket(self, project_id: str, name: str) -> Optional[BackendBucket]:
        return self.backend_buckets.get(project_id, {}).get(name)

    def list_backend_buckets(self, project_id: str) -> List[BackendBucket]:
        return list(self.backend_buckets.get(project_id, {}).values())

    def delete_backend_bucket(self, project_id: str, name: str) -> bool:
        with self._lock:
            if name in self.backend_buckets.get(project_id, {}):
                del self.backend_buckets[project_id][name]
                return True
            return False

    def get_cached(self, bucket_name: str, object_name: str, ttl_seconds: int) -> Optional[CacheEntry]:
        key = f"{bucket_name}/{object_name}"
        entry = self.cache.get(key)
        if entry and entry.is_fresh(ttl_seconds):
            entry.hit_count += 1
            self.hits += 1
            return entry
        self.misses += 1
        return None

    def put_cached(self, bucket_name: str, object_name: str, content: bytes, content_type: str) -> CacheEntry:
        key = f"{bucket_name}/{object_name}"
        entry = CacheEntry(content=content, content_type=content_type)
        with self._lock:
            self.cache[key] = entry
        return entry

    def invalidate(self, bucket_name: str, object_name: Optional[str] = None) -> int:
        with self._lock:
            if object_name:
                key = f"{bucket_name}/{object_name}"
                if key in self.cache:
                    del self.cache[key]
                    return 1
                return 0
            keys = [k for k in self.cache if k.startswith(f"{bucket_name}/")]
            for k in keys:
                del self.cache[k]
            return len(keys)

    def get_stats(self) -> Dict[str, int]:
        return {
            "backendBuckets": sum(len(b) for b in self.backend_buckets.values()),
            "cachedObjects": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
        }


storage = CdnStorage()
