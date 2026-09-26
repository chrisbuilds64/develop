"""Content pipeline: folders are stages, subfolders are pieces.

A live directory scan, so `as_of` is now — the numbers are as fresh as the
disk. Stage names follow the `NN-name` convention; anything else is ignored.
"""

from __future__ import annotations

import re

from . import now_iso

STAGE = re.compile(r"^(\d{2})-(.+)$")


def read(access, role, module, config) -> dict:
    src = module.sources[0]
    stages = []
    for name in access.listdir(src, role):
        m = STAGE.match(name)
        if not m:
            continue
        pieces = [p for p in access.listdir(src, role, name) if not p.startswith("_")]
        stages.append((int(m.group(1)), name, len(pieces)))
    stages.sort()

    by = {n: c for _, n, c in stages}
    # In flight: everything between the first working stage and scheduling —
    # archive (00) and the published stages (60+) are not work in progress.
    in_flight = sum(c for num, _, c in stages if 5 <= num <= 55)
    review = sum(c for n, c in by.items() if n.startswith("30-"))
    assets = sum(c for n, c in by.items() if n.startswith("40-"))
    published = sum(c for n, c in by.items() if n.startswith("60-"))

    return {
        "title": "pipeline.title",
        "subtitle": "pipeline.subtitle",
        "as_of": now_iso(),
        "state": "attention" if review >= 8 else "ok",
        "headline": {"value": in_flight, "unit": "pipeline.in_flight"},
        "lines": [
            {"label": "pipeline.review", "value": review, "tone": "warn" if review >= 8 else "muted"},
            {"label": "pipeline.assets", "value": assets, "tone": "muted"},
            {"label": "pipeline.published", "value": published, "tone": "ok"},
            {"label": "pipeline.stages", "value": len(stages), "tone": "muted"},
        ],
        "source": f"{access.source(src).label} · {len(stages)} folders",
        "figure": {"kind": "flow", "steps": [
            {"label": n.split("-", 1)[1].replace("-", " "), "value": c,
             "tone": "warn" if n.startswith("30-") else "muted" if num >= 60 else "accent"}
            for num, n, c in stages
        ]},
    }


def _pieces(access, role, src, stage):
    """Every piece in a stage, with what its meta.json says — if it has one."""
    out = []
    for name in access.listdir(src, role, stage):
        if name.startswith("_"):
            continue
        meta = {}
        try:
            if "meta.json" in access.listdir(src, role, f"{stage}/{name}"):
                meta = access.read_json(src, f"{stage}/{name}/meta.json", role)
        except Exception:
            meta = {}
        out.append({
            "tag": meta.get("number") or meta.get("label") or name.split("-", 1)[0],
            "title": meta.get("title") or name,
            "meta": [m for m in (meta.get("show"), meta.get("track"), meta.get("publishDate")) if m],
            "href": f"/m/pipeline/doc/{stage}/{name}",
        })
    return out


def detail(access, role, module, config) -> dict:
    src = module.sources[0]
    columns = []
    for name in access.listdir(src, role):
        m = STAGE.match(name)
        if not m:
            continue
        num = int(m.group(1))
        columns.append({
            "label": name.split("-", 1)[1].replace("-", " "),
            "tone": "warn" if num == 30 else "ok" if num >= 60 else "",
            "cards": _pieces(access, role, src, name),
        })
    return {"blocks": [
        {"kind": "kanban", "title": "block.by_stage", "columns": columns},
        {"kind": "links", "title": "block.tools", "items": [
            {"label": "tool.pressroom", "href": "pressroom://", "note": "drag & drop, macOS", "external": True},
            {"label": "tool.folder", "href": f"file://{access.source(src).path.expanduser()}", "external": True},
        ]},
    ]}


def document(access, role, module, config, ref) -> dict | None:
    """A piece: its meta plus every text file it carries, in order."""
    src = module.sources[0]
    stage, _, name = ref.partition("/")
    files = access.listdir(src, role, f"{stage}/{name}")
    meta = access.read_json(src, f"{stage}/{name}/meta.json", role) if "meta.json" in files else {}
    parts = [f"# {meta.get('title', name)}", ""]
    if meta.get("subtitle"):
        parts += [f"*{meta['subtitle']}*", ""]
    parts += [f"`{stage}` · `{name}`", ""]
    parts += ["| file | size |", "|---|---|"]
    for f in files:
        p = access.resolve(src, f"{stage}/{name}/{f}", role)
        parts.append(f"| `{f}` | {p.stat().st_size // 1024 or 1} KB |")
    for f in files:
        if f.endswith((".md", ".txt")) and f not in ("meta.json",):
            body = access.read_text(src, f"{stage}/{name}/{f}", role)
            parts += ["", "---", "", f"## {f}", "", body[:6000] + ("\n\n*… truncated*" if len(body) > 6000 else "")]
    return {"title": meta.get("title", name), "body": "\n".join(parts)}
