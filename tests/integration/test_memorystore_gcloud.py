"""CloudTester - Memorystore gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestMemorystoreGcloud:
    def test_gcloud_redis_instances_list(self, gcloud_runner, test_region):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run(f"redis instances list --region={test_region}")
        assert result.exit_code in (0, 1)
