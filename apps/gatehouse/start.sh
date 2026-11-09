#!/usr/bin/env bash
# Local launcher for the ChrisBuilds64 instance. Not in version control:
# it encodes one client's paths. The pattern is documented in
# docs/runbooks/gatehouse/setup.md, section 4.
set -euo pipefail

KEY_FILE="$HOME/.secrets/chrisbuilds64/chrisbuilds64.antrophic.api"

if [[ ! -r "$KEY_FILE" ]]; then
  echo "Schlüsseldatei nicht lesbar: $KEY_FILE" >&2
  exit 1
fi

# Read from the file, never from the command line: an exported value
# typed at a prompt ends up in shell history.
ANTHROPIC_API_KEY="$(tr -d '[:space:]' < "$KEY_FILE")"
export ANTHROPIC_API_KEY

cd "$(dirname "$0")"
exec .venv/bin/python -m gatehouse gatehouse.toml "$@"
