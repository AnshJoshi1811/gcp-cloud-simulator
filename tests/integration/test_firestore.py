"""
CloudTester - Firestore Tests
Tests for Firestore: document CRUD and structured queries.
"""

import pytest

pytestmark = pytest.mark.integration

DATABASE = "(default)"


class TestDocuments:
    def test_create_get_delete_document(self, api_client, test_project):
        path = f"/v1/projects/{test_project}/databases/{DATABASE}/documents/users?documentId=u1"
        resp = api_client.post(path, {"fields": {"name": {"stringValue": "Alice"}}})
        assert resp.status_code == 200, resp.text
        doc = resp.json()
        assert doc["fields"]["name"]["stringValue"] == "Alice"

        resp = api_client.get(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/users/u1"
        )
        assert resp.status_code == 200

        resp = api_client.delete(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/users/u1"
        )
        assert resp.status_code == 200

        resp = api_client.get(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/users/u1"
        )
        assert resp.status_code == 404

    def test_create_document_auto_id(self, api_client, test_project):
        resp = api_client.post(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/items",
            {"fields": {"sku": {"stringValue": "abc"}}},
        )
        assert resp.status_code == 200, resp.text
        assert "/items/" in resp.json()["name"]

    def test_list_documents(self, api_client, test_project):
        api_client.post(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/list-test",
            {"fields": {"x": {"integerValue": "1"}}},
        )
        resp = api_client.get(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/list-test"
        )
        assert resp.status_code == 200
        assert len(resp.json()["documents"]) >= 1

    def test_merge_update(self, api_client, test_project):
        doc_id = "merge-doc"
        api_client.post(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/merge?documentId={doc_id}",
            {"fields": {"a": {"integerValue": "1"}, "b": {"integerValue": "2"}}},
        )
        resp = api_client.patch(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/merge/{doc_id}?updateMask.fieldPaths=b",
            {"fields": {"b": {"integerValue": "99"}}},
        )
        assert resp.status_code == 200
        fields = resp.json()["fields"]
        assert fields["a"]["integerValue"] == "1"
        assert fields["b"]["integerValue"] == "99"


class TestQueries:
    def test_run_query_equality_filter(self, api_client, test_project):
        api_client.post(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/query-test?documentId=qt1",
            {"fields": {"status": {"stringValue": "active"}}},
        )
        api_client.post(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents/query-test?documentId=qt2",
            {"fields": {"status": {"stringValue": "inactive"}}},
        )
        resp = api_client.post(
            f"/v1/projects/{test_project}/databases/{DATABASE}/documents:runQuery",
            {
                "structuredQuery": {
                    "from": [{"collectionId": "query-test"}],
                    "where": {
                        "fieldFilter": {
                            "field": {"fieldPath": "status"},
                            "op": "EQUAL",
                            "value": {"stringValue": "active"},
                        }
                    },
                }
            },
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["document"]["fields"]["status"]["stringValue"] == "active"
