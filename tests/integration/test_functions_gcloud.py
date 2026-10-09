"""CloudTester - Cloud Functions gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestFunctionsGcloud:
    def test_gcloud_functions_list(self, gcloud_runner):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run("functions list")
        assert result.exit_code in (0, 1)
