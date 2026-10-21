#!/usr/bin/env bash
# Regenerate the surface's API types from the core's OpenAPI. CI runs it and fails on drift (ADR-014).
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import json, tempfile
from pathlib import Path
from casefile.api.app import Settings, create_app
from tests.world import CONFIG, build
root = build(Path(tempfile.mkdtemp()) / "flow")
app = create_app(Settings(root=root, config_dir=CONFIG, secret="x", recover_on_start=False))
Path("web/openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
PY
npx -y openapi-typescript@7 web/openapi.json -o web/src/api-types.d.ts >/dev/null
if [ "${1:-}" = "--check" ]; then git diff --exit-code -- web/openapi.json web/src/api-types.d.ts || { echo "API types drifted: run scripts/types.sh and commit"; exit 1; }; fi
echo "types: web/src/api-types.d.ts"
