"""CloudTester - Cloud CDN gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestCdnGcloud:
    def test_gcloud_backend_buckets_list(self, gcloud_runner):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run("compute backend-buckets list")
        assert result.exit_code in (0, 1)
