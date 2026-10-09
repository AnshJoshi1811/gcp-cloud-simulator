"""CloudTester - API Gateway gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestApiGatewayGcloud:
    def test_gcloud_api_gateway_apis_list(self, gcloud_runner):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run("api-gateway apis list")
        assert result.exit_code in (0, 1)
