#!/usr/bin/env python3
"""The architecture guard: the core does not know the outside (canon/software/architecture-guidelines.md, AG-4).

    python3 tools/arch_guard.py        fail when a core module imports an adapter, the API layer or a web framework

The casefile core is `domain/`, `store/` and `models.py`. It may import the standard library, pydantic and itself. The
edge (`api/`, `connectors/`, `cli/`, `demo/`) wires the core to the world; the core never reaches out to it. Read with the
AST, so a word in a comment or a string is not an import.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = "casefile"
CORE = ["apps/casefile/casefile/domain", "apps/casefile/casefile/store", "apps/casefile/casefile/models.py"]
FORBIDDEN = ("casefile.api", "casefile.connectors", "casefile.cli", "casefile.demo", "fastapi", "starlette", "uvicorn")


def _absolute(mod: str, level: int, here: Path, root: Path) -> str:
    """`from ..connectors import x` inside casefile/domain/a.py → casefile.connectors."""
    if not level:
        return mod
    parts = list(here.relative_to(root).with_suffix("").parts)[:-level]
    return ".".join(parts + ([mod] if mod else []))


def violations(root: Path = REPO) -> list[str]:
    out = []
    pkg_root = root / "apps/casefile"
    for base in CORE:
        p = root / base
        for f in ([p] if p.is_file() else sorted(p.rglob("*.py"))) if p.exists() else []:
            tree = ast.parse(f.read_text(encoding="utf-8"), str(f))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [_absolute(node.module or "", node.level, f, pkg_root)]
                for n in names:
                    if any(n == x or n.startswith(x + ".") for x in FORBIDDEN):
                        out.append(f"{f.relative_to(root)}:{node.lineno}: imports {n}")
    return out


def main() -> int:
    v = violations()
    if v:
        print("Architecture guard: the core reaches out to the edge (AG-4).", *v, sep="\n  ")
        print("\nMove the dependency to the edge and pass it in, or put a narrow interface in the core.")
        return 1
    print("Architecture guard: clean — the core imports no adapter, API layer or web framework.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
