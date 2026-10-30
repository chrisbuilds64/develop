"""The architecture guard (AG-4) and the contract (AG-1): the core does not import the edge, and the committed OpenAPI is
the one the core serves — the surface's types are generated from it."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

from casefile.api.app import Settings, create_app
from tests.world import CONFIG, build

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("arch_guard", REPO / "tools" / "arch_guard.py")
arch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arch)


def test_the_core_imports_nothing_from_the_edge():
    assert arch.violations() == []


def test_an_adapter_import_in_the_core_fails(tmp_path):
    core = tmp_path / "apps/casefile/casefile/domain"
    core.mkdir(parents=True)
    (core / "bad.py").write_text("# fastapi in a comment is fine\nfrom ..connectors import mailbox\nimport fastapi\n")
    (core / "good.py").write_text("import json\nfrom ..store import FsStore\nfrom casefile.config import DomainConfig\n")
    found = arch.violations(tmp_path)
    assert found == ["apps/casefile/casefile/domain/bad.py:2: imports casefile.connectors",
                     "apps/casefile/casefile/domain/bad.py:3: imports fastapi"]


def test_the_committed_contract_is_the_one_the_core_serves():
    root = build(Path(tempfile.mkdtemp()) / "flow")
    served = create_app(Settings(root=root, config_dir=CONFIG, secret="x", recover_on_start=False)).openapi()
    committed = json.loads((REPO / "apps/casefile/web/openapi.json").read_text(encoding="utf-8"))
    assert served == committed, "the API contract drifted: run apps/casefile/scripts/types.sh and commit both files"
