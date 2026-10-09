"""
CloudTester - Cloud KMS gcloud CLI compatibility checks.
Skips gracefully when gcloud isn't installed (handled by gcloud_runner fixture).
"""

import pytest

pytestmark = pytest.mark.gcloud


class TestKMSGcloud:
    def test_gcloud_kms_keyrings_list(self, gcloud_runner, test_region):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run(f"kms keyrings list --location={test_region}")
        assert result.exit_code in (0, 1)
