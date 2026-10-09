"""
CloudTester - API Gateway Tests
Tests for API Gateway: configs, gateways, and live request proxying to
deployed Cloud Functions.
"""

import time
import pytest

pytestmark = pytest.mark.integration

FN_SOURCE = "def handler(request):\n    return {'hi': 'from function'}, 200\n"


class TestApiGateway:
    def _suffix(self):
        return str(int(time.time() * 1000))

    def _deploy_function(self, api_client, test_project, test_region, name):
        resp = api_client.post(
            f"/functions/v1/projects/{test_project}/locations/{test_region}/functions",
            {"name": name, "entryPoint": "handler", "sourceCode": FN_SOURCE},
        )
        assert resp.status_code == 200, resp.text

    def test_full_gateway_chain_proxies_to_function(self, api_client, test_project, test_region):
        suffix = self._suffix()
        fn_name = f"gw-fn-{suffix}"
        self._deploy_function(api_client, test_project, test_region, fn_name)

        api_id = f"api-{suffix}"
        config_id = f"cfg-{suffix}"
        resp = api_client.post(
            f"/apigateway/v1/projects/{test_project}/apis/{api_id}/configs",
            {
                "configId": config_id,
                "routes": [{"path": "/hello", "method": "GET", "backendFunction": fn_name}],
            },
        )
        assert resp.status_code == 200, resp.text

        gateway_id = f"gw-{suffix}"
        resp = api_client.post(
            f"/apigateway/v1/projects/{test_project}/locations/{test_region}/gateways",
            {"gatewayId": gateway_id, "apiConfig": config_id},
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.get(f"/apigateway/v1/invoke/{test_project}/{gateway_id}/hello")
        assert resp.status_code == 200, resp.text
        assert resp.json()["hi"] == "from function"

    def test_unmatched_route_returns_404(self, api_client, test_project, test_region):
        suffix = self._suffix()
        fn_name = f"gw-fn2-{suffix}"
        self._deploy_function(api_client, test_project, test_region, fn_name)

        api_id = f"api2-{suffix}"
        config_id = f"cfg2-{suffix}"
        api_client.post(
            f"/apigateway/v1/projects/{test_project}/apis/{api_id}/configs",
            {
                "configId": config_id,
                "routes": [{"path": "/hello", "method": "GET", "backendFunction": fn_name}],
            },
        )
        gateway_id = f"gw2-{suffix}"
        api_client.post(
            f"/apigateway/v1/projects/{test_project}/locations/{test_region}/gateways",
            {"gatewayId": gateway_id, "apiConfig": config_id},
        )

        resp = api_client.get(f"/apigateway/v1/invoke/{test_project}/{gateway_id}/nope")
        assert resp.status_code == 404

    def test_config_requires_backend(self, api_client, test_project):
        resp = api_client.post(
            f"/apigateway/v1/projects/{test_project}/apis/bad-api/configs",
            {"configId": "bad-cfg", "routes": [{"path": "/x", "method": "GET"}]},
        )
        assert resp.status_code == 400

    def test_gateway_unknown_config_returns_404(self, api_client, test_project, test_region):
        resp = api_client.post(
            f"/apigateway/v1/projects/{test_project}/locations/{test_region}/gateways",
            {"gatewayId": f"bad-gw-{self._suffix()}", "apiConfig": "does-not-exist"},
        )
        assert resp.status_code == 404
