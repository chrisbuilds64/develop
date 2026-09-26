"""Content pipeline: folders are stages, subfolders are pieces.

A live directory scan. `as_of` is the time the pipeline last moved — the
newest modification under the stage folders, two levels down — so the card
says how old the *content* is, not how old the reading is. Stage names follow
the `NN-name` convention; anything else is ignored.
"""

from __future__ import annotations

import datetime as dt
import re

IMAGES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
VIDEOS = (".mp4", ".mov", ".webm")
TEXT = (".md", ".txt", ".json")


# The cover: every piece gets one, drawn from its meta — colour by track, glyph by type,
# the number large, the series as a band. Deterministic: the same meta is the same cover,
# today and in a year. These defaults are overridden by cover.json at the pipeline root,
# where the canon will keep them.
COVER = {
    "track": {"deep-tech": "#2f6fed", "provocative": "#e0a52a", "business": "#2fa36b", "weekend-notes": "#8a5cf6"},
    "label": {"FN": "field note", "POD": "podcast", "SP": "short post", "WN": "weekend note"},
    "fallback": "#5a6270",
}
GLYPH = {
    "FN": '<path d="M9 8h10M9 13h10M9 18h6"/>',
    "POD": '<rect x="11" y="4" width="6" height="11" rx="3"/><path d="M7 12a7 7 0 0 0 14 0M14 19v3"/>',
    "SP": '<path d="M15 3 7 15h6l-1 7 8-12h-6z"/>',
    "WN": '<path d="M5 20c0-8 4-14 14-15-1 10-6 14-14 15zM5 20c4-5 7-8 10-10"/>',
}


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def cover_svg(meta: dict, rules: dict | None = None, size: int = 96) -> str:
    """One piece as a small poster: 3:4, colour, glyph, number, series band, two lines of title."""
    r = {**COVER, **(rules or {})}
    label = str(meta.get("label") or "")
    colour = r["track"].get(str(meta.get("track") or ""), r["fallback"])
    number = str(meta.get("number") or "")
    series = str(meta.get("series") or "")
    title = str(meta.get("title") or "")
    words, lines, cur = title.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 16 and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
        if len(lines) == 2:
            break
    if cur and len(lines) < 2:
        lines.append(cur)
    if len(" ".join(lines)) < len(title) and lines:
        lines[-1] = lines[-1][:14] + "…"
    w, h = size, int(size * 4 / 3)
    glyph = GLYPH.get(label, '<circle cx="14" cy="13" r="6"/>')
    parts = [f'<svg class="cover" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{_esc(title)}">',
             f'<rect width="{w}" height="{h}" rx="{size // 12}" fill="{colour}"/>',
             f'<rect width="{w}" height="{h}" rx="{size // 12}" fill="url(#g{abs(hash(number + label)) % 9973})" opacity=".35"/>',
             f'<defs><linearGradient id="g{abs(hash(number + label)) % 9973}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient></defs>',
             f'<g transform="translate({size * 0.10} {size * 0.10}) scale({size / 96 * 0.9})" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity=".9">{glyph}</g>',
             f'<text x="{w - size * 0.10}" y="{size * 0.30}" text-anchor="end" font-family="ui-monospace, Menlo, monospace" font-size="{size * 0.11}" fill="#fff" opacity=".85">{_esc(label)}</text>',
             f'<text x="{size * 0.10}" y="{h * 0.56}" font-family="-apple-system, Inter, sans-serif" font-weight="800" font-size="{size * (0.30 if len(number) <= 3 else 0.22)}" fill="#fff">{_esc(number)}</text>']
    for i, line in enumerate(lines):
        parts.append(f'<text x="{size * 0.10}" y="{h * 0.70 + i * size * 0.13}" font-family="-apple-system, Inter, sans-serif" font-size="{size * 0.105}" fill="#fff" opacity=".92">{_esc(line)}</text>')
    if series:
        parts.append(f'<rect x="0" y="{h - size * 0.16}" width="{w}" height="{size * 0.16}" fill="#000" opacity=".28"/>')
        parts.append(f'<text x="{size * 0.10}" y="{h - size * 0.05}" font-family="ui-monospace, Menlo, monospace" font-size="{size * 0.10}" fill="#fff">{_esc(series)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _cover_rules(access, role, src) -> dict | None:
    try:
        if "cover.json" in access.listdir(src, role):
            return access.read_json(src, "cover.json", role)
    except Exception:
        pass
    return None


def _kind(name: str) -> str:
    n = name.lower()
    if n.endswith(IMAGES):
        return "image"
    if n.endswith(VIDEOS):
        return "video"
    if n == "meta.json" or n.endswith(".json"):
        return "data"
    if n == "review.md":
        return "review"
    if n.endswith(".md"):
        return "text"
    if n.endswith(".txt"):
        return "plain"
    if n.endswith((".pdf",)):
        return "pdf"
    return "other"

STAGE = re.compile(r"^(\d{2})-(.+)$")
VERSION = re.compile(r"\.v(\d+)\.")


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
        "as_of": dt.datetime.fromtimestamp(access.newest(src, role)).astimezone().isoformat(timespec="seconds"),
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


def _filters(access, role, src) -> list[dict]:
    """The fields the board filters by, straight from meta.schema.json at the pipeline root.

    Every property with a value list becomes a select; no schema, no filters. The
    surface never invents a value: what is not in the list cannot be chosen.
    """
    try:
        if "meta.schema.json" not in access.listdir(src, role):
            return []
        schema = access.read_json(src, "meta.schema.json", role)
    except Exception:
        return []
    out = []
    for name, prop in schema.get("properties", {}).items():
        if isinstance(prop, dict) and prop.get("enum") and not prop.get("deprecated"):
            out.append({"name": name, "label": name, "values": [str(v) for v in prop["enum"]]})
    return out


def _pieces(access, role, src, stage, facets=()):
    """Every piece in a stage, with what its meta.json says — if it has one.

    One read per piece and the reads in parallel: over a network mount each is
    a round trip, and ninety of them in a row are the difference between a
    second and fifteen.
    """
    from concurrent.futures import ThreadPoolExecutor
    names = [n for n in access.listdir(src, role, stage) if not n.startswith("_")]

    def meta_of(name):
        try:
            return access.read_json(src, f"{stage}/{name}/meta.json", role)
        except Exception:
            return {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        metas = list(pool.map(meta_of, names))
    rules = _cover_rules(access, role, src)
    out = []
    for name, meta in zip(names, metas):
        out.append({
            "cover": cover_svg(meta, rules, 64) if meta else "",
            # label + number is the whole tag — three pieces can share number "SIM-01"
            "tag": " ".join(str(x) for x in (meta.get("label"), meta.get("number")) if x) or name.split("-", 1)[0],
            "title": meta.get("title") or name,
            "meta": [m for m in (meta.get("show"), meta.get("track"), meta.get("publishDate")) if m],
            "href": f"/m/pipeline/doc/{stage}/{name}",
            "facets": {f: str(meta[f]) for f in facets if meta.get(f) is not None},
        })
    return out


def detail(access, role, module, config) -> dict:
    src = module.sources[0]
    filters = _filters(access, role, src)
    facets = [f["name"] for f in filters]
    columns = []
    for name in access.listdir(src, role):
        m = STAGE.match(name)
        if not m:
            continue
        num = int(m.group(1))
        columns.append({
            "label": name.split("-", 1)[1].replace("-", " "),
            "tone": "warn" if num == 30 else "ok" if num >= 60 else "",
            "cards": _pieces(access, role, src, name, facets),
        })
    blocks = [{"kind": "kanban", "title": "block.by_stage", "columns": columns, "filters": filters}]
    runs = _runs(access, role, src)
    if runs:
        blocks.append({"kind": "table", "title": "block.runs", "place": "actions", "columns": ["run.when", "run.skill", "run.container", "run.by", "run.status"],
                       "rows": [[r.get("created", "")[:16].replace("T", " "), "/" + r.get("skill", "?"),
                                 {"text": r.get("container", ""), "href": f"/m/pipeline/doc/{r.get('container', '')}"},
                                 r.get("requested_by", ""),
                                 {"badge": r.get("status", "?"), "tone": {"done": "ok", "failed": "bad", "running": "warn"}.get(r.get("status"), "muted")}]
                                for r in runs]})
    return {"blocks": blocks + [
        {"kind": "links", "title": "block.tools", "items": [
            {"label": "tool.pressroom", "href": "pressroom://", "note": "drag & drop, macOS", "external": True},
            {"label": "tool.folder", "href": f"file://{access.source(src).path.expanduser()}", "external": True},
        ]},
    ]}


def _runs(access, role, src, limit=12) -> list[dict]:
    """The newest orders in _runs/ — the queue and its history, one file each."""
    try:
        names = [n for n in access.listdir(src, role, "_runs") if n.endswith(".json")]
    except Exception:
        return []
    out = []
    for n in sorted(names, reverse=True)[:limit]:
        try:
            out.append(access.read_json(src, f"_runs/{n}", role))
        except Exception:
            continue
    return out


def document(access, role, module, config, ref) -> dict | None:
    """stage/name → the piece: meta and its files as links. stage/name/file → that file."""
    src = module.sources[0]
    parts = ref.split("/")
    if len(parts) == 3:
        stage, name, fname = parts
        if not fname.endswith((".md", ".txt", ".json")):
            return None
        body = access.read_text(src, ref, role)
        if fname.endswith(".json"):
            body = "```json\n" + body + "\n```"
        elif fname.endswith(".txt"):
            body = "```\n" + body + "\n```"
        return {"title": f"{name} · {fname}", "body": body}
    if len(parts) != 2:
        return None
    stage, name = parts
    files = access.listdir(src, role, f"{stage}/{name}")
    meta = access.read_json(src, f"{stage}/{name}/meta.json", role) if "meta.json" in files else {}
    parts_md = [f"# {meta.get('title', name)}", ""]
    if meta.get("subtitle"):
        parts_md += [f"*{meta['subtitle']}*", ""]
    parts_md += [f"`{stage}` · `{name}`"]
    tiles = []
    for f in files:
        p = access.resolve(src, f"{stage}/{name}/{f}", role)
        kind = _kind(f)
        if kind in ("image", "video", "pdf"):
            href = f"/m/{module.id}/file/{stage}/{name}/{f}"
        elif kind in ("data", "review", "text", "plain"):
            href = f"/m/{module.id}/doc/{stage}/{name}/{f}"
        else:
            href = ""
        tiles.append({"name": f, "kind": kind, "href": href, "size_kb": max(1, p.stat().st_size // 1024),
                      "version": (VERSION.search(f).group(1) if VERSION.search(f) else "")})
    if meta:
        parts_md += ["", "## meta.json", "", "| field | value |", "|---|---|"]
        for k, v in meta.items():
            parts_md.append(f"| `{k}` | {str(v)[:120].replace('|', '\\|')} |")
    out = {"title": meta.get("title", name), "body": "\n".join(parts_md)}
    if meta:
        out["cover"] = cover_svg(meta, _cover_rules(access, role, src), 160)
    if tiles:
        out["files"] = tiles
    return out
