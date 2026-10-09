"""
CloudTester - Cloud Logging Tests
Tests for Cloud Logging: entries.write/list and sinks.
"""

import time
import pytest

pytestmark = pytest.mark.integration


class TestEntries:
    def test_write_and_list_entries(self, api_client, test_project):
        log_name = f"projects/{test_project}/logs/app-{int(time.time() * 1000)}"
        resp = api_client.post(
            "/v2/entries:write",
            {
                "logName": log_name,
                "entries": [
                    {"textPayload": "hello world", "severity": "INFO"},
                    {"textPayload": "uh oh", "severity": "ERROR"},
                ],
            },
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.post(
            "/v2/entries:list",
            {"resourceNames": [f"projects/{test_project}"], "filter": f'logName="{log_name.split("/")[-1]}"'},
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 2

    def test_filter_by_severity(self, api_client, test_project):
        log_name = f"severity-test-{int(time.time() * 1000)}"
        api_client.post(
            "/v2/entries:write",
            {
                "logName": f"projects/{test_project}/logs/{log_name}",
                "entries": [
                    {"textPayload": "debug msg", "severity": "DEBUG"},
                    {"textPayload": "critical msg", "severity": "CRITICAL"},
                ],
            },
        )
        resp = api_client.post(
            "/v2/entries:list",
            {
                "resourceNames": [f"projects/{test_project}"],
                "filter": f'logName="{log_name}" AND severity>=ERROR',
            },
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["severity"] == "CRITICAL"

    def test_json_payload_entry(self, api_client, test_project):
        log_name = f"json-test-{int(time.time() * 1000)}"
        resp = api_client.post(
            "/v2/entries:write",
            {
                "logName": f"projects/{test_project}/logs/{log_name}",
                "entries": [{"jsonPayload": {"event": "login", "userId": "u1"}}],
            },
        )
        assert resp.status_code == 200

        resp = api_client.post(
            "/v2/entries:list",
            {"resourceNames": [f"projects/{test_project}"], "filter": f'logName="{log_name}"'},
        )
        entries = resp.json()["entries"]
        assert entries[0]["jsonPayload"]["event"] == "login"


class TestSinks:
    def test_create_list_delete_sink(self, api_client, test_project):
        sink_id = f"test-sink-{int(time.time() * 1000)}"
        resp = api_client.post(
            f"/v2/projects/{test_project}/sinks",
            {"name": sink_id, "destination": "storage.googleapis.com/my-bucket"},
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.get(f"/v2/projects/{test_project}/sinks")
        assert resp.status_code == 200
        assert any(s["name"].endswith(sink_id) for s in resp.json()["sinks"])

        resp = api_client.delete(f"/v2/projects/{test_project}/sinks/{sink_id}")
        assert resp.status_code == 200

        resp = api_client.get(f"/v2/projects/{test_project}/sinks/{sink_id}")
        assert resp.status_code == 404
