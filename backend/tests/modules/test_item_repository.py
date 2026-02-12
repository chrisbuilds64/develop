"""
ItemRepository unit tests.

Tests repository logic using MockDatabaseAdapter.
"""
import pytest
from modules.item_manager.repository import ItemRepository
from modules.item_manager.models import Item
from adapters.database.mock import MockDatabaseAdapter


class TestItemRepository:

    @pytest.fixture
    def repo(self):
        db = MockDatabaseAdapter()
        return ItemRepository(db)

    @pytest.fixture
    def saved_item(self, repo):
        item = Item(owner_id="user-1", label="Test Item", content_type="text/plain")
        return repo.save(item)

    def test_save_returns_item_with_id(self, repo):
        item = Item(owner_id="u1", label="New")
        saved = repo.save(item)
        assert saved.id is not None

    def test_find_by_id(self, repo, saved_item):
        found = repo.find_by_id(saved_item.id)
        assert found is not None
        assert found.label == "Test Item"

    def test_find_by_id_excludes_soft_deleted(self, repo, saved_item):
        repo.delete(saved_item.id, hard=False)
        assert repo.find_by_id(saved_item.id) is None

    def test_soft_delete(self, repo, saved_item):
        result = repo.delete(saved_item.id, hard=False)
        assert result is True
        assert saved_item.deleted_at is not None

    def test_hard_delete(self, repo, saved_item):
        result = repo.delete(saved_item.id, hard=True)
        assert result is True

    def test_update_sets_updated_at(self, repo, saved_item):
        saved_item.label = "Updated"
        updated = repo.update(saved_item)
        assert updated.updated_at is not None
        assert updated.label == "Updated"

    def test_delete_nonexistent(self, repo):
        assert repo.delete("nonexistent", hard=False) is False
