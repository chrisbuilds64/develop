"""Test data: a stage is a clone of production, taken on the disk, announced to Nextcloud.

The premise (Chris, 2026-10-24): a developer always has representative data. For the PressRoom that is
the production pipeline as it stands — every container, every review thread, every image — copied to
the stage's own team folder. The copy is a snapshot; nothing ever flows back. What is not copied: the
run queue (`_runs/`), because an order placed on PROD must not execute a second time on TEST.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import time
from pathlib import Path

from .config import Env, OpsError, Settings
from .nextcloud import TeamFolders
from .shell import run

log = logging.getLogger("pressroom-env")
FLOW = "flow"


def clone(settings: Settings, src: Env, dst: Env, folders: TeamFolders) -> dict:
    if not dst.clone_from:
        raise OpsError(f"stage '{dst.name}' is not a clone target (clone_from is empty) — production is never overwritten")
    ids = folders.list()
    for e in (src, dst):
        if e.folder not in ids:
            raise OpsError(f"team folder '{e.folder}' for stage {e.name} does not exist — run `create {e.name}` first")
    src_files, dst_files = folders.files(ids[src.folder]), folders.files(ids[dst.folder])
    if not (src_files / FLOW).is_dir():
        raise OpsError(f"{src_files / FLOW} is missing — is {src.folder} really the pipeline?")
    dst_files.mkdir(parents=True, exist_ok=True)
    owner = f"{settings.server.nextcloud_user}:{settings.server.nextcloud_user}"

    t0 = time.monotonic()
    r = run(["rsync", "-a", "--delete", "--stats", f"--chown={owner}",
             "--exclude", f"/{FLOW}/_runs/*", "--exclude", "*.claim",
             f"{src_files}/", f"{dst_files}/"])
    stats = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in r.stdout.splitlines() if ":" in l)}
    (dst_files / FLOW / "_runs").mkdir(exist_ok=True)
    shutil.chown(dst_files / FLOW / "_runs", *owner.split(":"))

    marker = {
        "environment": dst.name, "label": dst.label, "cloned_from": src.name,
        "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "$comment": "Written by pressroom-env clone. This pipeline is a snapshot of another stage; nothing here flows back.",
    }
    p = dst_files / FLOW / "environment.json"
    p.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.chown(p, *owner.split(":"))

    folders.scan(ids[dst.folder])
    out = {"files": stats.get("Number of files", "?"), "transferred": stats.get("Total transferred file size", "?"),
           "seconds": round(time.monotonic() - t0, 1)}
    log.info("cloned %s → %s: %s files, %s transferred, %.1f s", src.name, dst.name, out["files"], out["transferred"], out["seconds"])
    return out
