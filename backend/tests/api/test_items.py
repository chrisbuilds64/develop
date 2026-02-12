"""
Item API integration tests.

Tests CRUD operations at /api/v1/items with MockDatabaseAdapter.
Uses client_with_db fixture for shared state across requests.
"""


class TestCreateItem:

    def test_create_item_success(self, client_with_db, auth_headers_chris, sample_item_data):
        response = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "Test Item"
        assert data["content_type"] == "text/plain"
        assert data["tags"] == ["test", "sample"]
        assert "id" in data
        assert data["owner_id"] == "mock-user-chris-123"

    def test_create_item_without_auth(self, client, sample_item_data):
        response = client.post("/api/v1/items", json=sample_item_data)
        assert response.status_code == 401

    def test_create_item_invalid_token(self, client, sample_item_data):
        response = client.post(
            "/api/v1/items", json=sample_item_data,
            headers={"Authorization": "Bearer invalid"},
        )
        assert response.status_code == 401


class TestListItems:

    def test_list_items_empty(self, client_with_db, auth_headers_chris):
        response = client_with_db.get("/api/v1/items", headers=auth_headers_chris)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_items_after_create(self, client_with_db, auth_headers_chris, sample_item_data):
        client_with_db.post("/api/v1/items", json=sample_item_data, headers=auth_headers_chris)
        response = client_with_db.get("/api/v1/items", headers=auth_headers_chris)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_list_items_without_auth(self, client):
        response = client.get("/api/v1/items")
        assert response.status_code == 401


class TestGetItem:

    def test_get_item_success(self, client_with_db, auth_headers_chris, sample_item_data):
        create_resp = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        item_id = create_resp.json()["id"]
        response = client_with_db.get(f"/api/v1/items/{item_id}", headers=auth_headers_chris)
        assert response.status_code == 200
        assert response.json()["id"] == item_id

    def test_get_nonexistent_item(self, client_with_db, auth_headers_chris):
        response = client_with_db.get("/api/v1/items/nonexistent", headers=auth_headers_chris)
        assert response.status_code == 404

    def test_get_other_users_item(self, client_with_db, auth_headers_chris, auth_headers_lars, sample_item_data):
        create_resp = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        item_id = create_resp.json()["id"]
        response = client_with_db.get(f"/api/v1/items/{item_id}", headers=auth_headers_lars)
        assert response.status_code == 404


class TestUpdateItem:

    def test_update_item_success(self, client_with_db, auth_headers_chris, sample_item_data):
        create_resp = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        item_id = create_resp.json()["id"]
        response = client_with_db.put(
            f"/api/v1/items/{item_id}",
            json={"label": "Updated Label"},
            headers=auth_headers_chris,
        )
        assert response.status_code == 200
        assert response.json()["label"] == "Updated Label"

    def test_update_other_users_item(self, client_with_db, auth_headers_chris, auth_headers_lars, sample_item_data):
        create_resp = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        item_id = create_resp.json()["id"]
        response = client_with_db.put(
            f"/api/v1/items/{item_id}",
            json={"label": "Hacked"},
            headers=auth_headers_lars,
        )
        assert response.status_code == 404


class TestDeleteItem:

    def test_delete_item_success(self, client_with_db, auth_headers_chris, sample_item_data):
        create_resp = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        item_id = create_resp.json()["id"]
        response = client_with_db.delete(f"/api/v1/items/{item_id}", headers=auth_headers_chris)
        assert response.status_code == 204

    def test_delete_other_users_item(self, client_with_db, auth_headers_chris, auth_headers_lars, sample_item_data):
        create_resp = client_with_db.post(
            "/api/v1/items", json=sample_item_data, headers=auth_headers_chris
        )
        item_id = create_resp.json()["id"]
        response = client_with_db.delete(f"/api/v1/items/{item_id}", headers=auth_headers_lars)
        assert response.status_code == 404
