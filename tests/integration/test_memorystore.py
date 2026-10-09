"""
CloudTester - Memorystore Tests
Tests for Memorystore: Redis instances.
"""

import time
import pytest

pytestmark = pytest.mark.integration


class TestRedisInstances:
    def test_create_and_get_instance(self, api_client, test_project, test_region):
        instance_id = f"test-redis-{int(time.time() * 1000)}"
        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/instances",
            {"instanceId": instance_id, "tier": "BASIC", "memorySizeGb": 1},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["tier"] == "BASIC"
        assert data["state"] in ("READY", "FAILED")

        resp = api_client.get(
            f"/v1/projects/{test_project}/locations/{test_region}/instances/{instance_id}"
        )
        assert resp.status_code == 200

    def test_list_instances(self, api_client, test_project, test_region):
        resp = api_client.get(f"/v1/projects/{test_project}/locations/{test_region}/instances")
        assert resp.status_code == 200
        assert isinstance(resp.json()["instances"], list)

    def test_unsupported_tier_errors(self, api_client, test_project, test_region):
        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/instances",
            {"instanceId": "bad-tier", "tier": "PREMIUM"},
        )
        assert resp.status_code == 400

    def test_delete_instance(self, api_client, test_project, test_region):
        instance_id = f"test-redis-delete-{int(time.time() * 1000)}"
        api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/instances",
            {"instanceId": instance_id},
        )
        resp = api_client.delete(
            f"/v1/projects/{test_project}/locations/{test_region}/instances/{instance_id}"
        )
        assert resp.status_code == 200

        resp = api_client.get(
            f"/v1/projects/{test_project}/locations/{test_region}/instances/{instance_id}"
        )
        assert resp.status_code == 404
