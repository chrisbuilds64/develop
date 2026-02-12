"""
MockDatabaseAdapter unit tests.
"""
import pytest
from adapters.database.mock import MockDatabaseAdapter
from modules.item_manager.models import Item


class TestMockDatabaseAdapter:

    @pytest.fixture
    def db(self):
        return MockDatabaseAdapter()

    @pytest.fixture
    def sample_item(self):
        return Item(owner_id="user-1", label="Test", content_type="text/plain")

    def test_save_assigns_id(self, db, sample_item):
        saved = db.save(sample_item)
        assert saved.id is not None

    def test_save_and_find_by_id(self, db, sample_item):
        saved = db.save(sample_item)
        found = db.find_by_id(saved.id)
        assert found is not None
        assert found.label == "Test"

    def test_find_by_id_nonexistent(self, db):
        assert db.find_by_id("nonexistent") is None

    def test_find_all_empty(self, db):
        assert db.find_all() == []

    def test_find_all_with_items(self, db):
        db.save(Item(owner_id="u1", label="A"))
        db.save(Item(owner_id="u1", label="B"))
        assert len(db.find_all()) == 2

    def test_find_all_pagination(self, db):
        for i in range(5):
            db.save(Item(owner_id="u1", label=f"Item {i}"))
        assert len(db.find_all(limit=3)) == 3
        assert len(db.find_all(limit=3, offset=3)) == 2

    def test_update(self, db, sample_item):
        saved = db.save(sample_item)
        saved.label = "Updated"
        db.update(saved)
        found = db.find_by_id(saved.id)
        assert found.label == "Updated"

    def test_delete(self, db, sample_item):
        saved = db.save(sample_item)
        assert db.delete(saved.id) is True
        assert db.find_by_id(saved.id) is None

    def test_delete_nonexistent(self, db):
        assert db.delete("nonexistent") is False

    def test_find_by_criteria(self, db):
        db.save(Item(owner_id="user-1", label="A", content_type="text/plain"))
        db.save(Item(owner_id="user-2", label="B", content_type="media/youtube"))
        results = db.find_by(owner_id="user-1")
        assert len(results) == 1
        assert results[0].label == "A"

    def test_find_by_ignores_unknown_criteria(self, db):
        db.save(Item(owner_id="user-1", label="A"))
        results = db.find_by(owner_id="user-1", nonexistent_field="value")
        assert len(results) == 1

    def test_clear(self, db):
        db.save(Item(owner_id="u1", label="A"))
        db.clear()
        assert db.find_all() == []
