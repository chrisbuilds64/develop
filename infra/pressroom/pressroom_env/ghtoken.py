"""A token for the agent's GitHub App, minted per run (ADR-028). Standard library and `openssl` only.

    python3 -m pressroom_env.ghtoken --app-id 123 --installation-id 456 --key /path/to/app.private-key.pem

Prints an installation token (valid one hour) and nothing else, so the runner can use this as an executable secret:
the file `GH_TOKEN` in its secrets directory is a two-line script that calls this. The private key never leaves the
server; the token dies with the run.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.request

API = "https://api.github.com"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def jwt(app_id: str, key: str, now: int | None = None) -> str:
    """The app's own JWT (RS256), valid nine minutes, signed by openssl with the private key file."""
    now = int(time.time()) if now is None else now
    head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps({"iat": now - 60, "exp": now + 540, "iss": str(app_id)}, separators=(",", ":")).encode())
    signing = f"{head}.{body}".encode()
    sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key], input=signing, capture_output=True, check=True).stdout
    return f"{head}.{body}.{b64(sig)}"


def installation_token(app_id: str, installation_id: str, key: str) -> str:
    req = urllib.request.Request(f"{API}/app/installations/{installation_id}/access_tokens", method="POST",
                                 headers={"Authorization": f"Bearer {jwt(app_id, key)}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "pressroom-env"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())["token"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ghtoken", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--app-id", required=True)
    p.add_argument("--installation-id", required=True)
    p.add_argument("--key", required=True)
    a = p.parse_args(argv)
    try:
        print(installation_token(a.app_id, a.installation_id, a.key))
    except Exception as exc:  # noqa: BLE001 — one line on stderr, no token on stdout
        print(f"ghtoken: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
