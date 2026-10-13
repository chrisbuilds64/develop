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
    title = str(meta.get("title") or meta.get("working_title") or "")
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
        if not isinstance(prop, dict) or prop.get("deprecated"):
            continue
        if prop.get("enum"):
            out.append({"name": name, "label": name, "values": [str(v) for v in prop["enum"]]})
        elif prop.get("x-ref") == "series":
            # the value list is the set of series heads — a series without a folder does not exist
            out.append({"name": name, "label": name, "values": sorted(_series_heads(access, role, src))})
    return out


def _series_heads(access, role, src) -> dict[str, dict]:
    """label → head, from series/<LABEL>/series.json at the pipeline root."""
    try:
        labels = [n for n in access.listdir(src, role, "series") if not n.startswith(".")]
    except Exception:
        return {}
    out = {}
    for label in labels:
        try:
            out[label] = access.read_json(src, f"series/{label}/series.json", role)
        except Exception:
            continue
    return out


def _folder_index(access, role, src) -> dict[str, str]:
    """name → stage for every piece folder, one listing per stage."""
    idx = {}
    for stage in access.listdir(src, role):
        if not STAGE.match(stage):
            continue
        for name in access.listdir(src, role, stage):
            if not name.startswith("_"):
                idx[name] = stage
    return idx


def _resolve_ref(ref: str, index: dict[str, str]) -> tuple[str, str] | None:
    """SP-SIM-01 → (stage, folder) — the folder whose name starts with the ref."""
    for name, stage in index.items():
        if name == ref or name.startswith(ref + "-"):
            return stage, name
    return None


def _series_rows(access, role, src, people: dict[str, str]) -> list[dict]:
    """Every series with where its pieces stand — the block above the board."""
    heads = _series_heads(access, role, src)
    if not heads:
        return []
    index = _folder_index(access, role, src)
    rows = []
    for label, head in sorted(heads.items()):
        by = {}
        planned = 0
        for piece in head.get("pieces", []):
            hit = _resolve_ref(piece.get("ref", ""), index)
            if hit:
                key = hit[0].split("-", 1)[1].replace("-", " ")
                by[key] = by.get(key, 0) + 1
            else:
                planned += 1
        progress = " · ".join(f"{n} {k}" for k, n in by.items()) + (f" · {planned} planned" if planned else "")
        rows.append([{"text": label, "href": f"/m/pipeline/doc/series/{label}"}, head.get("title", label),
                     {"badge": head.get("status", "?"), "tone": {"running": "ok", "planned": "muted", "complete": "muted", "dormant": "warn"}.get(head.get("status"), "muted")},
                     people.get(head.get("editor", ""), head.get("editor", "")), progress or "—"])
    return rows


def _people(access, role, src) -> dict[str, str]:
    try:
        return {x["id"]: x["name"] for x in access.read_json(src, "people.json", role).get("people", [])}
    except Exception:
        return {}


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
            "title": meta.get("title") or meta.get("working_title") or name,
            "meta": [m for m in (meta.get("show"), meta.get("track"), meta.get("publishDate")) if m],
            "href": f"/m/pipeline/doc/{stage}/{name}",
            "facets": {f: str(meta[f]) for f in facets if meta.get(f) is not None},
            "date": str(meta.get("publishDate") or "")[:10],
            "published": int(STAGE.match(stage).group(1)) >= 60,
        })
    return out


def _calendar(access, role, src, columns, weeks_back=2, weeks_ahead=6) -> dict | None:
    """The weeks around today with every dated piece on its day; free slots and gaps below.

    Built from the board's cards, so it costs no extra read. Dates come from publishDate:
    planned before 60-published, published from there on. The rhythm — slots, one per day,
    the longest tolerable gap — is calendar.json at the pipeline root.
    """
    try:
        cal = access.read_json(src, "calendar.json", role) if "calendar.json" in access.listdir(src, role) else {}
    except Exception:
        cal = {}
    slots = [s[:3].title() for s in cal.get("slots", [])]
    max_gap = int(cal.get("max_gap_days", 0) or 0)
    today = dt.date.today()
    start = today - dt.timedelta(days=today.weekday() + 7 * weeks_back)
    by_day: dict[str, list] = {}
    for col in columns:
        for k in col["cards"]:
            if k.get("date"):
                by_day.setdefault(k["date"], []).append({"tag": k["tag"], "title": k["title"], "href": k["href"],
                                                         "state": "published" if k["published"] else "planned"})
    weeks, free = [], []
    for w in range(weeks_back + weeks_ahead):
        row = []
        for i in range(7):
            day = start + dt.timedelta(days=7 * w + i)
            iso = day.isoformat()
            wd = day.strftime("%a")
            is_slot = wd in slots
            if is_slot and day >= today and iso not in by_day and len(free) < 4:
                free.append(iso)
            row.append({"date": iso, "weekday": wd, "slot": is_slot, "today": day == today, "pieces": by_day.get(iso, [])})
        weeks.append(row)
    gaps = []
    if max_gap:
        dated = sorted(d for d in by_day if start.isoformat() <= d)
        dated = [dt.date.fromisoformat(d) for d in dated]
        for a, b in zip(dated, dated[1:]):
            if (b - a).days > max_gap:
                gaps.append({"from": a.isoformat(), "to": b.isoformat(), "days": (b - a).days})
        if dated and (today - dated[-1]).days > max_gap and all(d < today for d in dated):
            gaps.append({"from": dated[-1].isoformat(), "to": today.isoformat(), "days": (today - dated[-1]).days})
    return {"kind": "calendar", "title": "block.calendar", "weeks": weeks, "free": free, "gaps": gaps, "slots": slots}


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
            # The archive holds collections, not pieces: shown as a count, opened on demand.
            "collapsed": num == 0,
        })
    blocks = [_ideas(access, role, src)]
    series_rows = _series_rows(access, role, src, _people(access, role, src))
    if series_rows:
        blocks.append({"kind": "table", "title": "block.series", "open": False,
                       "columns": ["series.label", "series.title", "series.status", "series.editor", "series.progress"],
                       "rows": series_rows})
    blocks.append({**_calendar(access, role, src, columns), "open": False})
    blocks.append({"kind": "kanban", "title": "block.by_stage", "columns": columns, "filters": filters})
    runs = _runs(access, role, src)
    if runs:
        blocks.append({"kind": "table", "title": "block.runs", "place": "actions", "columns": ["run.when", "run.skill", "run.container", "run.by", "run.status", "run.cost"],
                       "rows": [[r.get("created", "")[:16].replace("T", " "), "/" + r.get("skill", "?"),
                                 {"text": r.get("container", ""), "href": f"/m/pipeline/doc/{r.get('container', '')}"},
                                 r.get("requested_by", ""),
                                 {"badge": r.get("status", "?"), "tone": {"done": "ok", "failed": "bad", "running": "warn"}.get(r.get("status"), "muted")},
                                 (f"{r['cost_usd']:.2f} $" if isinstance(r.get("cost_usd"), (int, float)) else "")]
                                for r in runs]})
    return {"blocks": blocks + [
        {"kind": "links", "title": "block.tools", "items": [
            {"label": "tool.pressroom", "href": "pressroom://", "note": "drag & drop, macOS", "external": True},
            {"label": "tool.folder", "href": f"file://{access.source(src).path.expanduser()}", "external": True},
        ]},
    ]}


def _ideas(access, role, src) -> dict:
    """The first block: every idea in 10-ideas — seed containers and loose notes — with its newest run.

    This is where a piece begins. A container shows its tag, title, date and who entered it;
    a loose .md file (a note someone dropped into the folder) is listed too, so nothing that
    sits in 10-ideas is invisible. The last column says whether an interpretation was ordered
    and how it went.
    """
    try:
        names = [n for n in access.listdir(src, role, "10-ideas") if not n.startswith((".", "_"))]
    except Exception:
        return {"kind": "table", "title": "block.ideas", "columns": ["idea.piece", "idea.title", "idea.created", "idea.origin", "idea.run"], "rows": []}
    last = _last_run_by_container(access, role, src)
    rows = []
    for name in sorted(names):
        path = access.resolve(src, f"10-ideas/{name}", role)
        href = f"/m/pipeline/doc/10-ideas/{name}"
        if path.is_file():
            if name.endswith(".md"):
                rows.append([{"text": name, "href": href}, {"badge": "idea.file", "tone": "muted"}, "", "", ""])
            continue
        try:
            meta = access.read_json(src, f"10-ideas/{name}/meta.json", role)
        except Exception:
            meta = {}
        tag = " ".join(str(x) for x in (meta.get("label"), meta.get("number") or meta.get("series")) if x) or name.split("-", 1)[0]
        run = last.get(f"10-ideas/{name}")
        state = ({"badge": run.get("status", "?"), "tone": {"done": "ok", "failed": "bad", "running": "warn"}.get(run.get("status"), "muted")}
                 if run else {"badge": "idea.none", "tone": "muted"})
        rows.append([{"text": tag, "href": href}, meta.get("title") or meta.get("working_title") or name,
                     str(meta.get("created") or "")[:10], str(meta.get("origin") or "")[:60], state])
    return {"kind": "table", "title": "block.ideas", "columns": ["idea.piece", "idea.title", "idea.created", "idea.origin", "idea.run"], "rows": rows}


def _last_run_by_container(access, role, src) -> dict[str, dict]:
    """container → its newest order in _runs/. Ids sort by time, so the last one wins."""
    out: dict[str, dict] = {}
    try:
        names = sorted(n for n in access.listdir(src, role, "_runs") if n.endswith(".json"))
    except Exception:
        return out
    for n in names:
        try:
            run = access.read_json(src, f"_runs/{n}", role)
        except Exception:
            continue
        if run.get("container"):
            out[run["container"]] = run
    return out


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
    if parts[0] == "series" and len(parts) == 2:
        return _series_page(access, role, module, src, parts[1])
    if len(parts) == 3:
        stage, name, fname = parts                       # stage/name/file — or series/<LABEL>/file
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
    if access.resolve(src, ref, role).is_file():
        if not name.endswith(".md"):
            return None
        return {"title": name, "body": access.read_text(src, ref, role), "file": True}
    files = access.listdir(src, role, f"{stage}/{name}")
    meta = access.read_json(src, f"{stage}/{name}/meta.json", role) if "meta.json" in files else {}
    parts_md = [f"# {meta.get('title', name)}", ""]
    if meta.get("subtitle"):
        parts_md += [f"*{meta['subtitle']}*", ""]
    parts_md += [f"`{stage}` · `{name}`"]
    if meta.get("series"):
        parts_md += ["", f"Series: [{meta['series']}](/m/{module.id}/doc/series/{meta['series']}) · {meta.get('label', '')}-{meta.get('number', '')}"]
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


def _series_page(access, role, module, src, label: str) -> dict | None:
    """series/<LABEL>: the head, then the pieces in the head's order with where each one stands, then the construct."""
    folder = f"series/{label}"
    try:
        files = access.listdir(src, role, folder)
    except Exception:
        return None
    head = access.read_json(src, f"{folder}/series.json", role) if "series.json" in files else {}
    people = _people(access, role, src)
    index = _folder_index(access, role, src)
    md = [f"# {head.get('title', label)}", ""]
    if head.get("spine"):
        md += [f"*{head['spine']}*", ""]
    line = [f"`{label}`", f"status **{head.get('status', '?')}**"]
    if head.get("editor"):
        line.append(f"editor {people.get(head['editor'], head['editor'])}")
    if head.get("sourced_by"):
        line.append("sourced by " + ", ".join(people.get(x, x) for x in head["sourced_by"]))
    md += [" · ".join(line), "", "## Pieces, in order of appearance", "", "| # | piece | role | title | stage | date |", "|---|---|---|---|---|---|"]
    for i, piece in enumerate(head.get("pieces", []), 1):
        ref = piece.get("ref", "")
        hit = _resolve_ref(ref, index)
        if hit:
            stage, name = hit
            try:
                meta = access.read_json(src, f"{stage}/{name}/meta.json", role)
            except Exception:
                meta = {}
            title = meta.get("title") or meta.get("working_title") or name
            md.append(f"| {i} | [{ref}](/m/{module.id}/doc/{stage}/{name}) | {piece.get('role', '')} | {title} | `{stage}` | {str(meta.get('publishDate') or '')[:10] or '—'} |")
        else:
            md.append(f"| {i} | {ref} | {piece.get('role', '')} | — | *planned, no container yet* | — |")
    if head.get("related"):
        md += ["", "Related: " + ", ".join(f"[{x}](/m/{module.id}/doc/series/{x})" for x in head["related"])]
    if "construct.md" in files:
        md += ["", "---", "", access.read_text(src, f"{folder}/construct.md", role)]
    tiles = []
    for f in files:
        p = access.resolve(src, f"{folder}/{f}", role)
        kind = _kind(f)
        href = f"/m/{module.id}/doc/{folder}/{f}" if kind in ("data", "review", "text", "plain") else (f"/m/{module.id}/file/{folder}/{f}" if kind in ("image", "video", "pdf") else "")
        tiles.append({"name": f, "kind": kind, "href": href, "size_kb": max(1, p.stat().st_size // 1024),
                      "version": (VERSION.search(f).group(1) if VERSION.search(f) else "")})
    out = {"title": head.get("title", label), "body": "\n".join(md),
           "cover": cover_svg({"label": label, "series": label, "title": head.get("title", label), "track": ""}, _cover_rules(access, role, src), 160)}
    if tiles:
        out["files"] = tiles
    return out


# ======================================================================= the desk
# The creator's view (concept: control/planning/2026-10-13_pressroom-bedienkonzept.md). The machine
# keeps its names — stage folders, labels, file names — and vocabulary.json at the pipeline root says
# what the desk calls them. A piece says what is next for the person and shows one button for it.

GROUP_OF_STAGE = {0: "archive", 5: "ideas", 10: "ideas", 15: "working", 20: "working", 30: "you",
                  40: "akhil", 50: "you", 55: "planned"}          # 60 and up: out
GROUPS = ("you", "working", "akhil", "planned", "ideas", "out")
SKILL_STAGES = {"interpret": ("10-ideas",), "canonical-review": ("60-published", "61-field-observation", "65-canonical-review"),
                "reflect": ("05-operational-observations",)}


def _vocab(access, role, src, lang: str) -> dict:
    try:
        v = access.read_json(src, "vocabulary.json", role) if "vocabulary.json" in access.listdir(src, role) else {}
    except Exception:
        v = {}
    return v.get(lang) or v.get("en") or {}


def _word(vocab: dict, kind: str, key: str, fallback: str | None = None) -> str:
    return (vocab.get(kind) or {}).get(key) or (fallback if fallback is not None else key)


def _file_word(vocab: dict, name: str) -> tuple[str, str]:
    """('LinkedIn-Post', '2') for linkedin-post.v2.txt — the vocabulary speaks about the unversioned name."""
    m = VERSION.search(name)
    base = name.replace(m.group(0), ".", 1) if m else name
    return _word(vocab, "files", base, base), (m.group(1) if m else "")


def _review_of(access, role, src, stage: str, name: str) -> list[dict]:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("review_entries", str(__import__("pathlib").Path(__file__).with_name("review_entries.py")))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.parse(access.read_text(src, f"{stage}/{name}/review.md", role))
    except Exception:
        return []


def _resolved_ids(entries: list[dict]) -> set[str]:
    return {e["resolves"] for e in entries if e.get("resolves")}


def _open_for(entries: list[dict], viewer: str | None) -> list[dict]:
    """Open entries addressed to the viewer that no later entry resolves."""
    done = _resolved_ids(entries)
    return [e for e in entries if e.get("status") == "open" and e["id"] not in done
            and (not viewer or (e.get("for") or "").lower() == viewer.lower())]


def _state(stage: str, run: dict | None, open_for_me: list[dict], has_image: bool, vocab: dict) -> dict:
    """The rule from the concept, §7: the first that applies wins. Returns group, state key and the one action."""
    num = int(STAGE.match(stage).group(1))
    if run and run.get("status") == "running":
        return {"group": "working", "state": "desk.state.running", "action": None}
    if run and run.get("status") == "failed" and num < 60:
        return {"group": "you", "state": "desk.state.failed", "action": {"kind": "link", "label": "desk.act.log", "href": f"/m/pipeline/doc/{run.get('log', '')}"}}
    if open_for_me:
        return {"group": "you", "state": "desk.state.open_notes", "n": len(open_for_me),
                "action": {"kind": "link", "label": "desk.act.answer", "href": "#notes"}}
    if num >= 60:
        return {"group": "out", "state": "desk.state.out", "action": None}
    group = GROUP_OF_STAGE.get(num, "ideas")
    action = None
    if stage == "10-ideas":
        action = {"kind": "form", "label": "desk.act.interpret", "action": "interpret", "fields": {}}
    elif num in (15, 20) and not run:
        action = {"kind": "form", "label": "desk.act.to_review", "action": "move", "module": True, "fields": {"stage": "30-review-human"}}
    elif num == 20:
        action = {"kind": "form", "label": "desk.act.to_review", "action": "move", "module": True, "fields": {"stage": "30-review-human"}}
    elif num == 30:
        action = {"kind": "link", "label": "desk.act.read", "href": None}
    elif num == 40 and has_image:
        action = {"kind": "form", "label": "desk.act.approve_image", "action": "move", "module": True, "fields": {"stage": "50-ready-to-publish"}}
    elif num == 50:
        action = {"kind": "form", "label": "desk.act.schedule", "action": "schedule", "fields": {"date": "?"}}
    elif num == 55:
        action = {"kind": "form", "label": "desk.act.published", "action": "move", "module": True, "fields": {"stage": "60-published"}}
    return {"group": group, "state": f"desk.stage.{stage}" if False else _word(vocab, "stages", stage), "action": action}


def desk(access, role, module, config, viewer: str | None = None, lang: str = "en") -> dict:
    """Every piece in the pipeline, grouped by what is next for the person. The desk's start page."""
    src = module.sources[0]
    vocab = _vocab(access, role, src, lang)
    rules = _cover_rules(access, role, src)
    runs = _last_run_by_container(access, role, src)
    groups: dict[str, list] = {g: [] for g in GROUPS}
    stages = sorted(n for n in access.listdir(src, role) if STAGE.match(n))
    for stage in stages:
        num = int(STAGE.match(stage).group(1))
        if num == 0:
            continue
        for name in sorted(n for n in access.listdir(src, role, stage) if not n.startswith(("_", "."))):
            if not access.resolve(src, f"{stage}/{name}", role).is_dir():
                continue
            try:
                meta = access.read_json(src, f"{stage}/{name}/meta.json", role)
            except Exception:
                meta = {}
            files = access.listdir(src, role, f"{stage}/{name}")
            run = runs.get(f"{stage}/{name}")
            entries = _review_of(access, role, src, stage, name) if "review.md" in files and num < 60 else []
            open_me = _open_for(entries, viewer)
            st = _state(stage, run, open_me, any(_kind(f) == "image" for f in files), vocab)
            href = f"/m/{module.id}/doc/{stage}/{name}"
            if st["action"] and st["action"].get("kind") == "link" and st["action"].get("href") is None:
                st["action"]["href"] = href
            if st["action"] and st["action"].get("href") == "#notes":
                st["action"]["href"] = href + "#notes"
            card = {
                "ref": f"{stage}/{name}", "href": href, "title": meta.get("title") or meta.get("working_title") or name,
                "format": _word(vocab, "labels", str(meta.get("label") or name.split("-", 1)[0])),
                "series": meta.get("series") or "", "date": str(meta.get("publishDate") or "")[:10],
                "created": str(meta.get("created") or "")[:10],
                "cover": cover_svg(meta, rules, 56) if meta else "", "state": st["state"], "n": st.get("n", 0),
                "action": st["action"], "run": {"status": run.get("status"), "cost": run.get("cost_usd")} if run else None,
                "group": st["group"],
            }
            groups[st["group"]].append(card)
    groups["planned"].sort(key=lambda c: c["date"])
    groups["out"].sort(key=lambda c: c["date"], reverse=True)
    groups["out"] = groups["out"][:12]
    return {"groups": [{"id": g, "cards": groups[g]} for g in GROUPS if groups[g]], "vocab": vocab}


def piece(access, role, module, config, ref: str, viewer: str | None = None, lang: str = "en") -> dict | None:
    """One piece, the creator's way: head with the one button, files in words, the notes as a thread, helpers."""
    src = module.sources[0]
    parts = ref.split("/")
    if len(parts) != 2 or not STAGE.match(parts[0]):
        return None
    stage, name = parts
    if not access.resolve(src, ref, role).is_dir():
        return None
    vocab = _vocab(access, role, src, lang)
    files = access.listdir(src, role, ref)
    meta = access.read_json(src, f"{ref}/meta.json", role) if "meta.json" in files else {}
    runs_all = [r for r in _all_runs(access, role, src) if r.get("container") == ref]
    run = runs_all[-1] if runs_all else None
    entries = _review_of(access, role, src, stage, name) if "review.md" in files else []
    open_me = _open_for(entries, viewer)
    st = _state(stage, run, open_me, any(_kind(f) == "image" for f in files), vocab)
    if st["action"] and st["action"].get("kind") == "link" and st["action"].get("href") in (None, "#notes"):
        st["action"] = None                                   # on the page itself, reading and answering are right here
    tiles = []
    for f in sorted(files):
        if f.startswith("."):
            continue
        p = access.resolve(src, f"{ref}/{f}", role)
        kind = _kind(f)
        href = (f"/m/{module.id}/file/{ref}/{f}" if kind in ("image", "video", "pdf")
                else f"/m/{module.id}/doc/{ref}/{f}" if kind in ("data", "review", "text", "plain") else "")
        label, version = _file_word(vocab, f)
        tiles.append({"name": f, "label": label, "version": version, "kind": kind, "href": href, "size_kb": max(1, p.stat().st_size // 1024)})
    resolved = _resolved_ids(entries)
    thread = [{**e, "resolved": e["id"] in resolved, "mine": bool(viewer) and (e.get("for") or "").lower() == (viewer or "").lower()} for e in entries]
    helpers = []
    try:
        policy = access.read_json(src, "run-policy.json", role)
        skills = access.read_json(src, "run.schema.json", role)["properties"]["skill"]["enum"]
    except Exception:
        policy, skills = {}, []
    for sk in skills:
        rule = {**policy.get("default", {}), **policy.get("skills", {}).get(sk, {})}
        if role.id not in rule.get("orderable_by", []):
            continue
        last = next((r for r in reversed(runs_all) if r.get("skill") == sk), None)
        helpers.append({"skill": sk, "fits": stage in SKILL_STAGES.get(sk, (stage,)),
                        "last": {"status": last.get("status"), "cost": last.get("cost_usd"), "when": last.get("created", "")[:16].replace("T", " "),
                                 "log": last.get("log", "")} if last else None})
    return {
        "ref": ref, "stage": stage, "name": name, "title": meta.get("title") or meta.get("working_title") or name,
        "format": _word(vocab, "labels", str(meta.get("label") or name.split("-", 1)[0])), "series": meta.get("series") or "",
        "number": str(meta.get("number") or ""), "date": str(meta.get("publishDate") or "")[:10], "created": str(meta.get("created") or "")[:10],
        "state": st["state"], "group": st["group"], "action": st["action"], "cover": cover_svg(meta, _cover_rules(access, role, src), 120) if meta else "",
        "files": tiles, "notes": thread, "open_for_me": [e["id"] for e in open_me], "helpers": helpers,
        "runs": [{"skill": r.get("skill"), "status": r.get("status"), "cost": r.get("cost_usd"), "when": r.get("created", "")[:16].replace("T", " "), "log": r.get("log", "")}
                 for r in runs_all[-6:]][::-1],
        "subtitle": meta.get("subtitle") or "", "origin": meta.get("origin") or "",
    }


def _all_runs(access, role, src) -> list[dict]:
    try:
        names = sorted(n for n in access.listdir(src, role, "_runs") if n.endswith(".json"))
    except Exception:
        return []
    out = []
    for n in names:
        try:
            out.append(access.read_json(src, f"_runs/{n}", role))
        except Exception:
            continue
    return out
