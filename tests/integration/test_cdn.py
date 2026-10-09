"""
CloudTester - Cloud CDN Tests
Tests for Cloud CDN: backend buckets and real cache MISS/HIT content serving
backed by an actual Cloud Storage object.
"""

import time
import pytest

pytestmark = pytest.mark.integration


class TestCdn:
    def _suffix(self):
        return str(int(time.time() * 1000))

    def test_backend_bucket_and_cache_hit_miss(self, api_client, test_project):
        suffix = self._suffix()
        bucket_name = f"cdn-bucket-{suffix}"
        object_name = "hello.txt"

        resp = api_client.post("/storage/v1/b?project=" + test_project, {"name": bucket_name})
        assert resp.status_code in (200, 201), resp.text

        resp = api_client.post(
            f"/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={object_name}",
            data=b"Hello CDN World",
        )
        assert resp.status_code in (200, 201), resp.text

        bb_name = f"cdn-bb-{suffix}"
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/backendBuckets",
            {"name": bb_name, "bucketName": bucket_name, "cdnPolicy": {"defaultTtl": 60}},
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.get(f"/cdn/v1/content/{bb_name}/{object_name}")
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("X-Cache") == "MISS"
        assert resp.content == b"Hello CDN World"

        resp = api_client.get(f"/cdn/v1/content/{bb_name}/{object_name}")
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache") == "HIT"
        assert resp.content == b"Hello CDN World"

    def test_invalidate_forces_next_miss(self, api_client, test_project):
        suffix = self._suffix()
        bucket_name = f"cdn-inv-bucket-{suffix}"
        object_name = "data.txt"

        api_client.post("/storage/v1/b?project=" + test_project, {"name": bucket_name})
        api_client.post(
            f"/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={object_name}",
            data=b"version-1",
        )
        bb_name = f"cdn-inv-bb-{suffix}"
        api_client.post(
            f"/compute/v1/projects/{test_project}/global/backendBuckets",
            {"name": bb_name, "bucketName": bucket_name},
        )
        resp = api_client.get(f"/cdn/v1/content/{bb_name}/{object_name}")
        assert resp.headers.get("X-Cache") == "MISS"
        resp = api_client.get(f"/cdn/v1/content/{bb_name}/{object_name}")
        assert resp.headers.get("X-Cache") == "HIT"

        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/backendBuckets/{bb_name}/invalidateCache", {}
        )
        assert resp.status_code == 200
        assert resp.json()["invalidatedCount"] >= 1

        resp = api_client.get(f"/cdn/v1/content/{bb_name}/{object_name}")
        assert resp.headers.get("X-Cache") == "MISS"

    def test_unknown_backend_bucket_returns_404(self, api_client):
        resp = api_client.get("/cdn/v1/content/does-not-exist/file.txt")
        assert resp.status_code == 404

    def test_object_not_found_in_bucket_returns_404(self, api_client, test_project):
        suffix = self._suffix()
        bucket_name = f"cdn-empty-bucket-{suffix}"
        api_client.post("/storage/v1/b?project=" + test_project, {"name": bucket_name})
        bb_name = f"cdn-empty-bb-{suffix}"
        api_client.post(
            f"/compute/v1/projects/{test_project}/global/backendBuckets",
            {"name": bb_name, "bucketName": bucket_name},
        )
        resp = api_client.get(f"/cdn/v1/content/{bb_name}/does-not-exist.txt")
        assert resp.status_code == 404
