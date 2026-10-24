"""Running commands as the right user, with the record that something ran.

Every call is logged before it runs (the command, the user) and on failure the tail of stderr is the
error message. The tool runs as root; Nextcloud's occ runs as the site user, git and pip as the
runner — never the other way round, because a root-owned file inside a user's tree is the kind of
fault that shows up a week later.
"""

from __future__ import annotations

import logging
import shlex
import subprocess

from .config import OpsError

log = logging.getLogger("pressroom-env")


def run(cmd: list[str], *, user: str | None = None, cwd: str | None = None, check: bool = True,
        env: dict | None = None, timeout: int = 1800, quiet: bool = False) -> subprocess.CompletedProcess:
    full = (["sudo", "-n", "-u", user, "-H"] + cmd) if user else cmd
    if not quiet:
        log.info("$ %s%s", f"[{user}] " if user else "", " ".join(shlex.quote(c) for c in cmd))
    try:
        r = subprocess.run(full, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise OpsError(f"command not found: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise OpsError(f"timed out after {timeout}s: {' '.join(cmd[:3])} …") from exc
    if check and r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-5:]
        raise OpsError(f"`{' '.join(cmd[:4])}` failed (exit {r.returncode}): " + " | ".join(tail))
    return r
