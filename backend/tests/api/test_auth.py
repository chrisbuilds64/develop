"""
Authentication edge case tests.

Tests auth header parsing and error responses.
"""


class TestAuthEdgeCases:

    def test_missing_authorization_header(self, client):
        response = client.get("/api/v1/items")
        assert response.status_code == 401

    def test_malformed_bearer_token(self, client):
        response = client.get(
            "/api/v1/items", headers={"Authorization": "NotBearer token"}
        )
        assert response.status_code == 401

    def test_bearer_without_token(self, client):
        response = client.get(
            "/api/v1/items", headers={"Authorization": "Bearer"}
        )
        assert response.status_code == 401

    def test_explicit_invalid_token(self, client):
        response = client.get(
            "/api/v1/items", headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401

    def test_valid_test_token_succeeds(self, client_with_db, auth_headers_chris):
        response = client_with_db.get("/api/v1/items", headers=auth_headers_chris)
        assert response.status_code == 200

    def test_different_users_get_different_ids(
        self, client_with_db, auth_headers_chris, auth_headers_lars, sample_item_data
    ):
        resp_chris = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        resp_lars = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_lars
        )
        assert resp_chris.json()["owner_id"] != resp_lars.json()["owner_id"]
