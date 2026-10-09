"""
CloudTester - Cloud Load Balancing Tests
Tests for Cloud Load Balancing: health checks, backend services, URL maps,
target proxies, forwarding rules, and simulated routing.
"""

import time
import pytest

pytestmark = pytest.mark.integration


class TestLoadBalancerChain:
    def _suffix(self):
        return str(int(time.time() * 1000))

    def test_full_lb_chain_and_simulate(self, api_client, test_project, test_zone):
        suffix = self._suffix()

        # Create a backing instance
        instance_name = f"lb-instance-{suffix}"
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/zones/{test_zone}/instances",
            {"name": instance_name, "machineType": "e2-micro", "zone": test_zone},
        )
        assert resp.status_code in (200, 201), resp.text

        hc_name = f"hc-{suffix}"
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/healthChecks", {"name": hc_name, "port": 80}
        )
        assert resp.status_code == 200, resp.text

        bs_name = f"bs-{suffix}"
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/backendServices",
            {"name": bs_name, "healthChecks": [hc_name]},
        )
        assert resp.status_code == 200, resp.text

        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/backendServices/{bs_name}/addBackend",
            {"instanceName": instance_name, "zone": test_zone, "port": 80},
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["backends"]) == 1

        um_name = f"um-{suffix}"
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/urlMaps",
            {"name": um_name, "defaultService": bs_name},
        )
        assert resp.status_code == 200, resp.text

        proxy_name = f"proxy-{suffix}"
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/targetHttpProxies",
            {"name": proxy_name, "urlMap": um_name},
        )
        assert resp.status_code == 200, resp.text

        rule_name = f"fr-{suffix}"
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/forwardingRules",
            {"name": rule_name, "target": proxy_name, "portRange": "80"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["IPAddress"]

        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/forwardingRules/{rule_name}:simulate"
        )
        assert resp.status_code == 200, resp.text
        result = resp.json()
        assert result["routedTo"] == instance_name
        assert "healthy" in result

    def test_simulate_with_no_backends_returns_409(self, api_client, test_project):
        suffix = self._suffix()
        bs_name = f"empty-bs-{suffix}"
        api_client.post(f"/compute/v1/projects/{test_project}/global/backendServices", {"name": bs_name})
        um_name = f"empty-um-{suffix}"
        api_client.post(
            f"/compute/v1/projects/{test_project}/global/urlMaps",
            {"name": um_name, "defaultService": bs_name},
        )
        proxy_name = f"empty-proxy-{suffix}"
        api_client.post(
            f"/compute/v1/projects/{test_project}/global/targetHttpProxies",
            {"name": proxy_name, "urlMap": um_name},
        )
        rule_name = f"empty-fr-{suffix}"
        api_client.post(
            f"/compute/v1/projects/{test_project}/global/forwardingRules",
            {"name": rule_name, "target": proxy_name},
        )
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/forwardingRules/{rule_name}:simulate"
        )
        assert resp.status_code == 409

    def test_simulate_unknown_rule_returns_404(self, api_client, test_project):
        resp = api_client.post(
            f"/compute/v1/projects/{test_project}/global/forwardingRules/does-not-exist:simulate"
        )
        assert resp.status_code == 404
