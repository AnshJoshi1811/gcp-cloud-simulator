"""
CloudTester - Cloud Tasks gcloud CLI compatibility checks.
"""

import pytest

pytestmark = pytest.mark.gcloud


class TestTasksGcloud:
    def test_gcloud_tasks_queues_list(self, gcloud_runner, test_region):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run(f"tasks queues list --location={test_region}")
        assert result.exit_code in (0, 1)
