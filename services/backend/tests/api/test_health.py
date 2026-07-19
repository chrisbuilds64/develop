"""
Health endpoint tests.

Smoke test: if this passes, Docker test setup is working.
"""


class TestHealthEndpoint:

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
