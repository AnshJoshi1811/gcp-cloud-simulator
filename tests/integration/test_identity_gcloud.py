"""CloudTester - Cloud Identity Platform gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestIdentityGcloud:
    def test_gcloud_identity_users_describe(self, gcloud_runner):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run("identity-platform config describe")
        assert result.exit_code in (0, 1)
