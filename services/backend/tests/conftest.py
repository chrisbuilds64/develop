"""
Test Configuration and Fixtures

Root conftest.py -- shared fixtures for all tests.
ENV=test is set via Docker environment, which activates:
  - MockDatabaseAdapter (in-memory storage)
  - MockAuthAdapter (test-chris, test-lars, test-lily tokens)
"""
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from api.main import app
from adapters.database.mock import MockDatabaseAdapter
from api.dependencies import get_database_adapter


# ============================================
# App Fixtures
# ============================================

@pytest.fixture
def client():
    """FastAPI TestClient with default dependency injection."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def shared_mock_db():
    """Shared MockDatabaseAdapter that persists across requests in one test."""
    return MockDatabaseAdapter()


@pytest.fixture
def client_with_db(shared_mock_db):
    """
    TestClient with shared MockDatabaseAdapter.
    Items created via POST persist for GET/PUT/DELETE in the same test.
    """
    app.dependency_overrides[get_database_adapter] = lambda: shared_mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ============================================
# Auth Fixtures
# ============================================

@pytest.fixture
def auth_headers_chris():
    return {"Authorization": "Bearer test-chris"}


@pytest.fixture
def auth_headers_lars():
    return {"Authorization": "Bearer test-lars"}


@pytest.fixture
def auth_headers_lily():
    return {"Authorization": "Bearer test-lily"}


# ============================================
# Data Fixtures
# ============================================

@pytest.fixture
def sample_item_data():
    return {
        "label": "Test Item",
        "content_type": "text/plain",
        "payload": {"text": "Hello World"},
        "tags": ["test", "sample"]
    }
