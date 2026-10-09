"""
CloudTester - Cloud SQL Tests
Tests for Cloud SQL: instances, databases, users.
"""

import time
import pytest

pytestmark = pytest.mark.integration


class TestInstances:
    def test_create_and_get_instance(self, api_client, test_project, test_region):
        instance_id = f"test-sql-{int(time.time() * 1000)}"
        resp = api_client.post(
            "/sql/v1beta4/projects/" + test_project + "/instances",
            {"name": instance_id, "region": test_region, "databaseVersion": "POSTGRES_15"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == instance_id
        assert data["state"] in ("RUNNABLE", "FAILED")

        resp = api_client.get(f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}")
        assert resp.status_code == 200

    def test_list_instances(self, api_client, test_project):
        resp = api_client.get(f"/sql/v1beta4/projects/{test_project}/instances")
        assert resp.status_code == 200
        assert isinstance(resp.json()["items"], list)

    def test_unsupported_database_version_errors(self, api_client, test_project):
        resp = api_client.post(
            f"/sql/v1beta4/projects/{test_project}/instances",
            {"name": "bad-instance", "databaseVersion": "ORACLE_19"},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_stop_and_start_instance(self, api_client, test_project, test_region):
        instance_id = f"test-sql-lifecycle-{int(time.time() * 1000)}"
        api_client.post(
            f"/sql/v1beta4/projects/{test_project}/instances",
            {"name": instance_id, "region": test_region, "databaseVersion": "MYSQL_8_0"},
        )
        resp = api_client.post(f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}:stop")
        assert resp.status_code == 200
        assert resp.json()["state"] == "STOPPED"

        resp = api_client.post(f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}:start")
        assert resp.status_code == 200
        assert resp.json()["state"] == "RUNNABLE"

    def test_delete_instance(self, api_client, test_project, test_region):
        instance_id = f"test-sql-delete-{int(time.time() * 1000)}"
        api_client.post(
            f"/sql/v1beta4/projects/{test_project}/instances",
            {"name": instance_id, "region": test_region, "databaseVersion": "POSTGRES_15"},
        )
        resp = api_client.delete(f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}")
        assert resp.status_code == 200

        resp = api_client.get(f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}")
        assert resp.status_code == 404


class TestDatabasesAndUsers:
    def _instance(self, api_client, test_project, test_region):
        instance_id = f"test-sql-db-{int(time.time() * 1000)}"
        api_client.post(
            f"/sql/v1beta4/projects/{test_project}/instances",
            {"name": instance_id, "region": test_region, "databaseVersion": "POSTGRES_15"},
        )
        return instance_id

    def test_create_list_delete_database(self, api_client, test_project, test_region):
        instance_id = self._instance(api_client, test_project, test_region)
        resp = api_client.post(
            f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}/databases", {"name": "appdb"}
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.get(f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}/databases")
        assert resp.status_code == 200
        assert any(d["name"] == "appdb" for d in resp.json()["items"])

        resp = api_client.delete(
            f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}/databases/appdb"
        )
        assert resp.status_code == 200

    def test_create_user_returns_password_once(self, api_client, test_project, test_region):
        instance_id = self._instance(api_client, test_project, test_region)
        resp = api_client.post(
            f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}/users", {"name": "appuser"}
        )
        assert resp.status_code == 200, resp.text
        assert "password" in resp.json()

        resp = api_client.get(f"/sql/v1beta4/projects/{test_project}/instances/{instance_id}/users")
        assert resp.status_code == 200
        assert any(u["name"] == "appuser" for u in resp.json()["items"])
