"""
CloudTester - Cloud Tasks Tests
Tests for Cloud Tasks: queues, tasks, dispatching.
"""

import time
import pytest

pytestmark = pytest.mark.integration


class TestQueues:
    def test_create_list_get_queue(self, api_client, test_project, test_region):
        queue_id = f"test-queue-{int(time.time() * 1000)}"
        resp = api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues",
            {"queueId": queue_id},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"].endswith(f"queues/{queue_id}")

        resp = api_client.get(f"/v2/projects/{test_project}/locations/{test_region}/queues")
        assert resp.status_code == 200
        assert isinstance(resp.json()["queues"], list)

        resp = api_client.get(f"/v2/projects/{test_project}/locations/{test_region}/queues/{queue_id}")
        assert resp.status_code == 200

    def test_pause_and_resume_queue(self, api_client, test_project, test_region):
        queue_id = f"pause-queue-{int(time.time() * 1000)}"
        api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues", {"queueId": queue_id}
        )
        resp = api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues/{queue_id}:pause"
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "PAUSED"

        resp = api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues/{queue_id}:resume"
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "RUNNING"

    def test_queue_not_found(self, api_client, test_project, test_region):
        resp = api_client.get(f"/v2/projects/{test_project}/locations/{test_region}/queues/does-not-exist")
        assert resp.status_code == 404


class TestTasks:
    def test_create_task_and_dispatch(self, api_client, test_project, test_region, base_url):
        queue_id = f"dispatch-queue-{int(time.time() * 1000)}"
        api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues", {"queueId": queue_id}
        )

        resp = api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues/{queue_id}/tasks",
            {"task": {"httpRequest": {"url": f"{base_url}/health", "httpMethod": "GET"}}},
        )
        assert resp.status_code == 200, resp.text
        task = resp.json()
        assert task["state"] == "SCHEDULED"
        task_name = task["name"]
        task_id = task_name.rsplit("/", 1)[-1]

        # Background dispatcher should pick this up within a couple seconds.
        for _ in range(10):
            time.sleep(0.5)
            resp = api_client.get(
                f"/v2/projects/{test_project}/locations/{test_region}/queues/{queue_id}/tasks/{task_id}"
            )
            if resp.json()["state"] == "SUCCEEDED":
                break
        assert resp.json()["state"] == "SUCCEEDED"

    def test_delete_task(self, api_client, test_project, test_region):
        queue_id = f"delete-queue-{int(time.time() * 1000)}"
        api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues", {"queueId": queue_id}
        )
        resp = api_client.post(
            f"/v2/projects/{test_project}/locations/{test_region}/queues/{queue_id}/tasks",
            {"task": {"httpRequest": {"url": "http://localhost:1/nope", "httpMethod": "GET"}}},
        )
        task_id = resp.json()["name"].rsplit("/", 1)[-1]
        resp = api_client.delete(
            f"/v2/projects/{test_project}/locations/{test_region}/queues/{queue_id}/tasks/{task_id}"
        )
        assert resp.status_code == 200
