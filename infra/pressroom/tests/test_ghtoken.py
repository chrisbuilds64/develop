"""The app's JWT is RS256 over header and claims, verifiable with the app's public key (ADR-028)."""

import base64
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pressroom_env import ghtoken  # noqa: E402


def unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def test_the_jwt_names_the_app_and_verifies_with_its_key(tmp_path):
    key, pub = tmp_path / "app.pem", tmp_path / "app.pub"
    subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], check=True, capture_output=True)
    subprocess.run(["openssl", "rsa", "-in", str(key), "-pubout", "-out", str(pub)], check=True, capture_output=True)
    token = ghtoken.jwt("4711", str(key), now=1_800_000_000)
    head, body, sig = token.split(".")
    assert json.loads(unb64(head)) == {"alg": "RS256", "typ": "JWT"}
    claims = json.loads(unb64(body))
    assert claims["iss"] == "4711" and claims["exp"] - claims["iat"] <= 600
    (tmp_path / "sig").write_bytes(unb64(sig))
    ok = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(tmp_path / "sig")],
                        input=f"{head}.{body}".encode(), capture_output=True)
    assert ok.returncode == 0
