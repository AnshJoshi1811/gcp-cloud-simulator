"""
CloudTester - Cloud Identity Platform Tests
Tests for Cloud Identity: sign-up, sign-in, lookup, user management.
"""

import time
import pytest

pytestmark = pytest.mark.integration


class TestIdentity:
    def _email(self):
        return f"user-{int(time.time() * 1000)}@example.com"

    def test_sign_up_and_sign_in(self, api_client, test_project):
        email = self._email()
        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signUp",
            {"email": email, "password": "s3cret123", "displayName": "Test User"},
        )
        assert resp.status_code == 200, resp.text
        assert "idToken" in resp.json()

        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signInWithPassword",
            {"email": email, "password": "s3cret123"},
        )
        assert resp.status_code == 200, resp.text
        assert "idToken" in resp.json()

    def test_sign_up_duplicate_email_errors(self, api_client, test_project):
        email = self._email()
        api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signUp",
            {"email": email, "password": "pw12345"},
        )
        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signUp",
            {"email": email, "password": "pw12345"},
        )
        assert resp.status_code == 409

    def test_sign_in_wrong_password_returns_401(self, api_client, test_project):
        email = self._email()
        api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signUp",
            {"email": email, "password": "correct-password"},
        )
        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signInWithPassword",
            {"email": email, "password": "wrong-password"},
        )
        assert resp.status_code == 401

    def test_lookup_with_token(self, api_client, test_project):
        email = self._email()
        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signUp",
            {"email": email, "password": "pw12345"},
        )
        token = resp.json()["idToken"]
        resp = api_client.post("/identitytoolkit/v1/accounts:lookup", {"idToken": token})
        assert resp.status_code == 200
        assert resp.json()["users"][0]["email"] == email

    def test_lookup_invalid_token_returns_401(self, api_client):
        resp = api_client.post("/identitytoolkit/v1/accounts:lookup", {"idToken": "not-a-real-token"})
        assert resp.status_code == 401

    def test_password_never_returned(self, api_client, test_project):
        email = self._email()
        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signUp",
            {"email": email, "password": "supersecret"},
        )
        body = resp.json()
        assert "password" not in body
        assert "supersecret" not in str(body)

    def test_disable_and_list_users(self, api_client, test_project):
        email = self._email()
        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signUp",
            {"email": email, "password": "pw12345"},
        )
        local_id = resp.json()["localId"]

        resp = api_client.get(f"/identitytoolkit/v1/projects/{test_project}/accounts")
        assert resp.status_code == 200
        assert any(u["localId"] == local_id for u in resp.json()["users"])

        resp = api_client.post(f"/identitytoolkit/v1/projects/{test_project}/accounts/{local_id}:disable")
        assert resp.status_code == 200
        assert resp.json()["disabled"] is True

        resp = api_client.post(
            f"/identitytoolkit/v1/projects/{test_project}/accounts:signInWithPassword",
            {"email": email, "password": "pw12345"},
        )
        assert resp.status_code == 401
