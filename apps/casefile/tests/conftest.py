import pytest

from casefile.config import DomainConfig
from casefile.store import FsStore

from .world import CONFIG, build


@pytest.fixture
def root(tmp_path):
    return build(tmp_path / "flow")


@pytest.fixture
def store(root):
    return FsStore(root)


@pytest.fixture
def config(root):
    return DomainConfig.load(root.parent / "config", root)
