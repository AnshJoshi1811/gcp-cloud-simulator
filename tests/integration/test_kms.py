"""
CloudTester - Cloud KMS Tests
Tests for Cloud KMS: key rings, crypto keys, versions, encrypt/decrypt
"""

import base64
import time
import pytest

pytestmark = pytest.mark.integration


class TestKeyRings:
    def test_create_and_get_key_ring(self, api_client, test_project, test_region):
        ring_id = f"test-ring-{int(time.time() * 1000)}"
        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings?keyRingId={ring_id}"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"].endswith(f"keyRings/{ring_id}")

        resp = api_client.get(f"/v1/projects/{test_project}/locations/{test_region}/keyRings/{ring_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == data["name"]

    def test_list_key_rings(self, api_client, test_project, test_region):
        resp = api_client.get(f"/v1/projects/{test_project}/locations/{test_region}/keyRings")
        assert resp.status_code == 200
        assert isinstance(resp.json().get("keyRings"), list)

    def test_duplicate_key_ring_errors(self, api_client, test_project, test_region):
        ring_id = f"dup-ring-{int(time.time() * 1000)}"
        path = f"/v1/projects/{test_project}/locations/{test_region}/keyRings?keyRingId={ring_id}"
        assert api_client.post(path).status_code == 200
        resp = api_client.post(path)
        assert resp.status_code == 409


class TestCryptoKeysAndEncryption:
    def _ring(self, api_client, test_project, test_region, ring_id):
        api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings?keyRingId={ring_id}"
        )

    def test_create_crypto_key_and_round_trip_encrypt(self, api_client, test_project, test_region):
        ring_id = f"enc-ring-{int(time.time() * 1000)}"
        key_id = "enc-key"
        self._ring(api_client, test_project, test_region, ring_id)

        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings/{ring_id}/cryptoKeys"
            f"?cryptoKeyId={key_id}",
            {"purpose": "ENCRYPT_DECRYPT"},
        )
        assert resp.status_code == 200, resp.text
        key = resp.json()
        assert key["purpose"] == "ENCRYPT_DECRYPT"
        assert "primary" in key

        plaintext = b"super secret value"
        plaintext_b64 = base64.b64encode(plaintext).decode()
        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings/{ring_id}/cryptoKeys/{key_id}:encrypt",
            {"plaintext": plaintext_b64},
        )
        assert resp.status_code == 200
        ciphertext_b64 = resp.json()["ciphertext"]
        assert ciphertext_b64 != plaintext_b64

        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings/{ring_id}/cryptoKeys/{key_id}:decrypt",
            {"ciphertext": ciphertext_b64},
        )
        assert resp.status_code == 200
        decrypted = base64.b64decode(resp.json()["plaintext"])
        assert decrypted == plaintext

    def test_crypto_key_version_lifecycle(self, api_client, test_project, test_region):
        ring_id = f"ver-ring-{int(time.time() * 1000)}"
        key_id = "ver-key"
        self._ring(api_client, test_project, test_region, ring_id)
        api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings/{ring_id}/cryptoKeys"
            f"?cryptoKeyId={key_id}",
            {},
        )

        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings/{ring_id}/cryptoKeys/{key_id}/cryptoKeyVersions"
        )
        assert resp.status_code == 200
        version = resp.json()
        version_id = version["name"].rsplit("/", 1)[-1]

        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings/{ring_id}/cryptoKeys/{key_id}/cryptoKeyVersions/{version_id}:destroy"
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "DESTROYED"

    def test_encrypt_missing_key_returns_404(self, api_client, test_project, test_region):
        resp = api_client.post(
            f"/v1/projects/{test_project}/locations/{test_region}/keyRings/nope/cryptoKeys/nope:encrypt",
            {"plaintext": "aGk="},
        )
        assert resp.status_code == 404
