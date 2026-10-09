"""
CloudTester - Firewall Tests
Tests for Firewall Rules (Phase 1: Default rules creation)
"""

from datetime import datetime

import pytest

pytestmark = pytest.mark.integration


class TestDefaultFirewallRules:
    """Test Default Firewall Rules Creation (Phase 1)"""
    
    def test_list_firewall_rules(self, api_client, test_project):
        """List all firewall rules"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls"
        resp = api_client.get(path)
        
        assert resp.status_code == 200
        data = resp.json()
        
        rules = data.get("items", [])
        assert isinstance(rules, list)
    
    def test_default_rules_exist(self, api_client, test_project):
        """Verify 5 default firewall rules are created"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls"
        resp = api_client.get(path)
        
        assert resp.status_code == 200
        data = resp.json()
        
        rules = data.get("items", [])
        rule_names = [r["name"] for r in rules]
        
        # Phase 1 requirements
        expected_rules = {
            "allow-ssh": {"protocol": "tcp", "ports": ["22"]},
            "allow-http": {"protocol": "tcp", "ports": ["80"]},
            "allow-https": {"protocol": "tcp", "ports": ["443"]},
            "allow-internal": {"protocol": "all"},
            "allow-icmp": {"protocol": "icmp"}
        }
        
        for rule_name in expected_rules.keys():
            assert rule_name in rule_names, f"Missing default rule: {rule_name}"
    
    def test_allow_ssh_rule(self, api_client, test_project):
        """Verify allow-ssh rule configuration"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls/allow-ssh"
        resp = api_client.get(path)
        
        if resp.status_code == 404:
            pytest.skip("allow-ssh rule not yet created")
        
        assert resp.status_code == 200
        rule = resp.json()
        
        assert rule["name"] == "allow-ssh"
        assert rule["direction"] == "INGRESS"
        assert "22" in str(rule.get("allowed", []))
    
    def test_allow_http_rule(self, api_client, test_project):
        """Verify allow-http rule configuration"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls/allow-http"
        resp = api_client.get(path)
        
        if resp.status_code == 404:
            pytest.skip("allow-http rule not yet created")
        
        assert resp.status_code == 200
        rule = resp.json()
        
        assert rule["name"] == "allow-http"
        assert "80" in str(rule.get("allowed", []))
    
    def test_allow_https_rule(self, api_client, test_project):
        """Verify allow-https rule configuration"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls/allow-https"
        resp = api_client.get(path)
        
        if resp.status_code == 404:
            pytest.skip("allow-https rule not yet created")
        
        assert resp.status_code == 200
        rule = resp.json()
        
        assert rule["name"] == "allow-https"
        assert "443" in str(rule.get("allowed", []))
    
    def test_allow_internal_rule(self, api_client, test_project):
        """Verify allow-internal rule configuration"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls/allow-internal"
        resp = api_client.get(path)
        
        if resp.status_code == 404:
            pytest.skip("allow-internal rule not yet created")
        
        assert resp.status_code == 200
        rule = resp.json()
        
        assert rule["name"] == "allow-internal"
        assert rule["sourceRanges"] == ["10.0.0.0/8"]
    
    def test_allow_icmp_rule(self, api_client, test_project):
        """Verify allow-icmp rule configuration"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls/allow-icmp"
        resp = api_client.get(path)
        
        if resp.status_code == 404:
            pytest.skip("allow-icmp rule not yet created")
        
        assert resp.status_code == 200
        rule = resp.json()
        
        assert rule["name"] == "allow-icmp"
        assert "icmp" in str(rule.get("allowed", []))


class TestCustomFirewallRules:
    """Test Custom Firewall Rules"""
    
    def test_create_custom_rule(self, api_client, test_project, sample_firewall_payload):
        """Create a custom firewall rule"""
        path = f"/compute/v1/projects/{test_project}/global/firewalls"
        
        resp = api_client.post(path, sample_firewall_payload)
        
        assert resp.status_code in [200, 201]
        rule = resp.json()
        
        assert rule["name"] == sample_firewall_payload["name"]
    
    def test_delete_custom_rule(self, api_client, test_project, sample_firewall_payload):
        """Delete a custom firewall rule"""
        # Create rule first
        create_path = f"/compute/v1/projects/{test_project}/global/firewalls"
        create_resp = api_client.post(create_path, sample_firewall_payload)
        
        if create_resp.status_code not in [200, 201]:
            pytest.skip("Cannot create rule")
        
        rule_name = sample_firewall_payload["name"]
        
        # Delete rule
        delete_path = f"/compute/v1/projects/{test_project}/global/firewalls/{rule_name}"
        delete_resp = api_client.delete(delete_path)
        
        assert delete_resp.status_code in [200, 204]


class TestFirewallValidation:
    """Validate create and patch guardrails for firewall rules."""

    def test_create_firewall_rule_invalid_priority(self, api_client, test_project):
        path = f"/compute/v1/projects/{test_project}/global/firewalls"
        payload = {
            "name": f"invalid-priority-{int(datetime.now().timestamp())}",
            "network": "default",
            "direction": "INGRESS",
            "priority": 70000,
            "sourceRanges": ["0.0.0.0/0"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["80"]}],
        }
        resp = api_client.post(path, payload)
        assert resp.status_code == 422

    def test_create_firewall_rule_invalid_direction(self, api_client, test_project):
        path = f"/compute/v1/projects/{test_project}/global/firewalls"
        payload = {
            "name": f"invalid-direction-{int(datetime.now().timestamp())}",
            "network": "default",
            "direction": "SIDEWAYS",
            "priority": 1000,
            "sourceRanges": ["0.0.0.0/0"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["80"]}],
        }
        resp = api_client.post(path, payload)
        assert resp.status_code == 422

    def test_create_firewall_rule_invalid_cidr(self, api_client, test_project):
        path = f"/compute/v1/projects/{test_project}/global/firewalls"
        payload = {
            "name": f"invalid-cidr-{int(datetime.now().timestamp())}",
            "network": "default",
            "direction": "INGRESS",
            "priority": 1000,
            "sourceRanges": ["10.0.0.0/99"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["80"]}],
        }
        resp = api_client.post(path, payload)
        assert resp.status_code == 422

    def test_patch_firewall_rule_priority(self, api_client, test_project):
        create_path = f"/compute/v1/projects/{test_project}/global/firewalls"
        rule_name = f"patch-priority-{int(datetime.now().timestamp())}"
        create_payload = {
            "name": rule_name,
            "network": "default",
            "direction": "INGRESS",
            "priority": 1000,
            "sourceRanges": ["0.0.0.0/0"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["8080"]}],
        }
        create_resp = api_client.post(create_path, create_payload)
        assert create_resp.status_code in [200, 201]

        patch_path = f"/compute/v1/projects/{test_project}/global/firewalls/{rule_name}"
        patch_resp = api_client.patch(patch_path, {"priority": 900})
        assert patch_resp.status_code == 200

        get_resp = api_client.get(patch_path)
        assert get_resp.status_code == 200
        assert get_resp.json().get("priority") == 900

    def test_firewall_rules_list_by_network(self, api_client, test_project):
        net_name = "default"
        firewall_path = f"/compute/v1/projects/{test_project}/global/firewalls"
        rule_name = f"filter-by-network-{int(datetime.now().timestamp())}"
        create_fw_resp = api_client.post(
            firewall_path,
            {
                "name": rule_name,
                "network": net_name,
                "direction": "INGRESS",
                "priority": 1001,
                "sourceRanges": ["0.0.0.0/0"],
                "allowed": [{"IPProtocol": "tcp", "ports": ["22"]}],
            },
        )
        assert create_fw_resp.status_code in [200, 201]

        list_resp = api_client.get(f"{firewall_path}?network={net_name}")
        assert list_resp.status_code == 200
        items = list_resp.json().get("items", [])
        assert any(item.get("name") == rule_name for item in items)
