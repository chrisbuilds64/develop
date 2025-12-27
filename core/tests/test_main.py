"""Tests for Tweight Core API endpoints."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    """Test /health endpoint returns OK status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "tweight-core"
    assert "version" in data


def test_timer():
    """Test /timer endpoint returns valid timestamp."""
    response = client.get("/timer")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "unix" in data
    assert isinstance(data["unix"], int)
