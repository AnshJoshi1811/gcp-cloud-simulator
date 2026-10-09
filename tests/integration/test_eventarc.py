"""
CloudTester - Event Routing (Eventarc-style) Tests
Tests a real Pub/Sub -> Cloud Functions event trigger: publishing to a topic
actually causes the destination function to be invoked, via the background
dispatcher polling a dedicated subscription.
"""

import base64
import json
import time
import pytest

pytestmark = pytest.mark.integration

FN_SOURCE = (
    "def handler(request):\n"
    "    data = request.get_json() or {}\n"
    "    return {'received': data}, 200\n"
)


class TestEventRouting:
    def _suffix(self):
        return str(int(time.time() * 1000))

    def test_publish_invokes_destination_function(self, api_client, test_project, test_region):
        suffix = self._suffix()
        topic_id = f"evt-topic-{suffix}"
        fn_name = f"evt-fn-{suffix}"
        trigger_id = f"evt-trigger-{suffix}"

        resp = api_client.post(
            f"/v1/projects/{test_project}/topics",
            {"name": f"projects/{test_project}/topics/{topic_id}"},
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.post(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions",
            {"name": fn_name, "entryPoint": "handler", "sourceCode": FN_SOURCE},
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.post(
            f"/eventarc/v1/projects/{test_project}/locations/{test_region}/triggers",
            {"triggerId": trigger_id, "topic": topic_id, "destinationFunction": fn_name},
        )
        assert resp.status_code == 200, resp.text

        payload = base64.b64encode(json.dumps({"hello": "event"}).encode()).decode()
        resp = api_client.post(
            f"/v1/projects/{test_project}/topics/{topic_id}:publish",
            {"messages": [{"data": payload}]},
        )
        assert resp.status_code == 200, resp.text

        trigger = None
        for _ in range(20):
            time.sleep(0.5)
            resp = api_client.get(
                f"/eventarc/v1/projects/{test_project}/locations/{test_region}/triggers/{trigger_id}"
            )
            trigger = resp.json()
            if trigger.get("eventCount", 0) >= 1:
                break
        assert trigger["eventCount"] >= 1, trigger

        resp = api_client.get(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions/{fn_name}"
        )
        assert resp.json()["invocationCount"] >= 1

    def test_create_trigger_unknown_topic_returns_404(self, api_client, test_project, test_region):
        resp = api_client.post(
            f"/eventarc/v1/projects/{test_project}/locations/{test_region}/triggers",
            {"triggerId": "bad-trigger", "topic": "does-not-exist", "destinationFunction": "x"},
        )
        assert resp.status_code == 404

    def test_delete_trigger(self, api_client, test_project, test_region):
        suffix = self._suffix()
        topic_id = f"del-topic-{suffix}"
        api_client.post(
            f"/v1/projects/{test_project}/topics",
            {"name": f"projects/{test_project}/topics/{topic_id}"},
        )
        trigger_id = f"del-trigger-{suffix}"
        api_client.post(
            f"/eventarc/v1/projects/{test_project}/locations/{test_region}/triggers",
            {"triggerId": trigger_id, "topic": topic_id, "destinationFunction": "whatever"},
        )
        resp = api_client.delete(
            f"/eventarc/v1/projects/{test_project}/locations/{test_region}/triggers/{trigger_id}"
        )
        assert resp.status_code == 200

        resp = api_client.get(
            f"/eventarc/v1/projects/{test_project}/locations/{test_region}/triggers/{trigger_id}"
        )
        assert resp.status_code == 404
