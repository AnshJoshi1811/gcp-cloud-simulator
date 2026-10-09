"""
CloudTester - Cloud Functions Tests
Tests for Cloud Functions: deploy, invoke, lifecycle. Runs via the in-process
execution fallback when Docker is unavailable, and via a real container when
it is — either way the HTTP invoke contract is the same.
"""

import time
import pytest

pytestmark = pytest.mark.integration

HELLO_SOURCE = (
    "def handler(request):\n"
    "    data = request.get_json() or {}\n"
    "    name = data.get('name', 'world')\n"
    "    return {'message': f'Hello, {name}!'}, 200\n"
)

ERROR_SOURCE = "def handler(request):\n    raise ValueError('boom')\n"


class TestFunctionLifecycle:
    def test_deploy_and_invoke(self, api_client, test_project, test_region):
        name = f"hello-fn-{int(time.time() * 1000)}"
        resp = api_client.post(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions",
            {"name": name, "entryPoint": "handler", "runtime": "python312", "sourceCode": HELLO_SOURCE},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["state"] == "ACTIVE"

        resp = api_client.post(
            f"/functions/v1/invoke/{test_project}/{test_region}/{name}", {"name": "Ansh"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["message"] == "Hello, Ansh!"

    def test_invoke_without_body_uses_default(self, api_client, test_project, test_region):
        name = f"hello-default-{int(time.time() * 1000)}"
        api_client.post(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions",
            {"name": name, "entryPoint": "handler", "sourceCode": HELLO_SOURCE},
        )
        resp = api_client.post(f"/functions/v1/invoke/{test_project}/{test_region}/{name}", {})
        assert resp.status_code == 200
        assert resp.json()["message"] == "Hello, world!"

    def test_function_exception_returns_error_not_crash(self, api_client, test_project, test_region):
        name = f"err-fn-{int(time.time() * 1000)}"
        api_client.post(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions",
            {"name": name, "entryPoint": "handler", "sourceCode": ERROR_SOURCE},
        )
        resp = api_client.post(f"/functions/v1/invoke/{test_project}/{test_region}/{name}", {})
        assert resp.status_code == 200  # server itself never crashes
        assert "error" in resp.json()

        # Server is still up and serving other requests afterwards.
        assert api_client.get("/health").status_code == 200

    def test_unsupported_runtime_returns_400(self, api_client, test_project, test_region):
        resp = api_client.post(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions",
            {"name": "bad-runtime-fn", "entryPoint": "handler", "runtime": "go121", "sourceCode": "x"},
        )
        assert resp.status_code == 400

    def test_invoke_unknown_function_returns_404(self, api_client, test_project, test_region):
        resp = api_client.post(
            f"/functions/v1/invoke/{test_project}/{test_region}/does-not-exist", {}
        )
        assert resp.status_code == 404

    def test_list_and_delete_function(self, api_client, test_project, test_region):
        name = f"delete-fn-{int(time.time() * 1000)}"
        api_client.post(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions",
            {"name": name, "entryPoint": "handler", "sourceCode": HELLO_SOURCE},
        )
        resp = api_client.get(f"/functions/v1/projects/{test_project}/locations/{test_region}/functions")
        assert resp.status_code == 200
        assert any(name in f["name"] for f in resp.json()["functions"])

        resp = api_client.delete(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions/{name}"
        )
        assert resp.status_code == 200

        resp = api_client.get(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions/{name}"
        )
        assert resp.status_code == 404
