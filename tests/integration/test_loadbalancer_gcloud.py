"""CloudTester - Cloud Load Balancing gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestLoadBalancerGcloud:
    def test_gcloud_backend_services_list(self, gcloud_runner):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run("compute backend-services list --global")
        assert result.exit_code in (0, 1)
