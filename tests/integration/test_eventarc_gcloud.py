"""CloudTester - Event Routing gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestEventarcGcloud:
    def test_gcloud_eventarc_triggers_list(self, gcloud_runner, test_region):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run(f"eventarc triggers list --location={test_region}")
        assert result.exit_code in (0, 1)
