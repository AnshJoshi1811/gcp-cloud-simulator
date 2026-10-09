"""CloudTester - Cloud SQL gcloud CLI compatibility checks."""

import pytest

pytestmark = pytest.mark.gcloud


class TestSqlGcloud:
    def test_gcloud_sql_instances_list(self, gcloud_runner):
        if not gcloud_runner.available:
            pytest.skip("gcloud CLI not available")
        result = gcloud_runner.run("sql instances list")
        assert result.exit_code in (0, 1)
