"""CloudTester - Cloud Logging gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestLoggingGcloud:
    def test_gcloud_logging_sinks_list(self, gcloud_runner):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run("logging sinks list")
        assert result.exit_code in (0, 1)
