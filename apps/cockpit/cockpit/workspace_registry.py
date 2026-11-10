"""The registry in the terms of ADR-032: connectors, workspaces with data points, application instances bound to them.

Format 2 of `workspaces.json` (format 1 had one flat list of entries, each one application over one tree):

    {"format": 2,
     "applications": {"pressroom": {"label": "PressRoom", "config_dir": "…", "template": "…", "mode": "live"}},
     "connectors":   {"nextcloud": {"kind": "nextcloud", "label": "…", "root": "/…/__groupfolders", "write_root": "/srv"},
                      "server":    {"kind": "directory", "label": "…", "root": ""}},
     "workspaces": [
       {"id": "operations", "label": "Betrieb", "open": false, "members": ["chris", "akhil"],
        "data_points": [{"name": "pressroom", "connector": "nextcloud", "place": "1/files/flow", "write_place": "pressroom/flow"}],
        "instances":   [{"id": "pressroom", "application": "pressroom", "label": "PressRoom", "mode": "live",
                         "bind": {"cases": "pressroom"}}]}]}

- A **connector** is the technical access: kind, root (and a root to write through, where writes take another way).
  Its root is absolute, or relative to the registry's directory ("" = that directory).
- A **data point** is a place on a connector, owned by its workspace, with readers and writers and an optional seed
  (the tree a sample is copied from).
- An **instance** runs an application and binds its slots: `cases` to one data point, or to several
  (`[{"point": "worklist-team", "as": "team"}, …]`, read together, ADR-032), and then `home` to the data point that
  carries the instance's own files. `members` narrows the workspace's members for this instance.
- A workspace that is `open` lets every signed-in person in (the samples); otherwise its members only.

`instances()` reads format 2 and gives every instance in the shape a format-1 entry had, so the cockpit, the runner
and pressroom-env keep one way of reading. `migrate()` writes format 2 from format 1 and a plan. Standard library
only: pressroom-env imports this module from the checkout, outside the cockpit's interpreter.
"""

from __future__ import annotations

import copy
from pathlib import Path, PurePosixPath

FORMAT = 2
COMMENT = ("The cockpit's registry (ADR-032, format 2): applications, connectors, and workspaces with their data points "
           "and application instances. Edited by `cockpit workspace …` and the cockpit itself; paths relative to this "
           "file's directory or absolute.")


class RegistryError(Exception):
    """A sentence for the person, never a stack trace."""


def is_v2(doc: dict) -> bool:
    return isinstance(doc, dict) and doc.get("format") == FORMAT


def _join(root: str, place: str | None) -> str | None:
    if place is None or place == "":
        return root or None
    if PurePosixPath(place).is_absolute() or not root:
        return place
    return str(PurePosixPath(root) / place)


def point_paths(doc: dict, point: dict) -> tuple[str, str | None]:
    """(root, write_root) of a data point, from its connector and its place. Relative = relative to the registry."""
    con = (doc.get("connectors") or {}).get(point.get("connector") or "")
    if con is None:
        raise RegistryError(f"data point '{point.get('name')}': connector '{point.get('connector')}' is not defined")
    root = _join(str(con.get("root") or ""), str(point.get("place") or ""))
    if not root:
        raise RegistryError(f"data point '{point.get('name')}' has no place")
    write = None
    if point.get("write_place"):
        if not con.get("write_root") and not PurePosixPath(str(point["write_place"])).is_absolute():
            raise RegistryError(f"data point '{point.get('name')}': write_place without a write_root on connector '{point.get('connector')}'")
        write = _join(str(con.get("write_root") or ""), str(point["write_place"]))
    return root, write


def _binding(cases) -> list[dict]:
    if isinstance(cases, str):
        return [{"point": cases}]
    if isinstance(cases, list):
        return [{"point": c} if isinstance(c, str) else dict(c) for c in cases]
    raise RegistryError("an instance binds `cases` to a data point or a list of them")


def instances(doc: dict) -> list[dict]:
    """Every instance of a format-2 registry as a format-1 entry, plus `workspace`, `workspace_label` and `template`."""
    out, seen = [], set()
    for ws in doc.get("workspaces") or []:
        wid = str(ws.get("id") or "")
        points = {}
        for p in ws.get("data_points") or []:
            if p.get("name") in points:
                raise RegistryError(f"workspace '{wid}': data point '{p.get('name')}' appears twice")
            points[p.get("name")] = p

        def get(name: str, inst: str) -> dict:
            if name not in points:
                raise RegistryError(f"instance '{inst}': data point '{name}' is not in workspace '{wid}'")
            return points[name]

        for i in ws.get("instances") or []:
            iid = str(i.get("id") or "")
            if iid in seen:
                raise RegistryError(f"instance '{iid}' appears twice — instance ids are unique across workspaces (they are the address /w/<id>/)")
            seen.add(iid)
            bind = i.get("bind") or {}
            cases = _binding(bind.get("cases"))
            members = list(i.get("members") or ws.get("members") or [])
            entry = {"id": iid, "application": i.get("application"), "label": i.get("label") or iid,
                     "shared": bool(ws.get("open", False)), "members": members, "mode": i.get("mode", "live"),
                     "open_identity": bool(ws.get("open_identity", False) or i.get("open_identity", False)),
                     "workspace": wid, "workspace_label": ws.get("label") or wid}
            for k in ("owner", "created", "cloned_from", "components"):
                if i.get(k):
                    entry[k] = i[k]
            if bind.get("home"):
                entry["root"], wr = point_paths(doc, get(bind["home"], iid))
                if wr:
                    entry["write_root"] = wr
                dps = []
                for c in cases:
                    p = get(c["point"], iid)
                    r, w = point_paths(doc, p)
                    dps.append({"name": c.get("as") or p["name"], "root": r, **({"write_root": w} if w else {}),
                                "readers": list(p.get("readers") or members), "writers": list(p.get("writers") or members),
                                **({"label": p["label"]} if p.get("label") else {})})
                entry["data_points"] = dps
            else:
                if len(cases) != 1:
                    raise RegistryError(f"instance '{iid}': several data points for `cases` need a `home`")
                p = get(cases[0]["point"], iid)
                entry["root"], wr = point_paths(doc, p)
                if wr:
                    entry["write_root"] = wr
            seed = next((get(c["point"], iid).get("seed") for c in cases if get(c["point"], iid).get("seed")), None)
            if seed:
                entry["template"] = seed
            out.append(entry)
    return out


# -------------------------------------------------------------------- from format 1

def _relative(path: str, root: str) -> str | None:
    """`path` below `root` as a relative place, or None when it is not below it."""
    if not root:
        return None
    try:
        return str(PurePosixPath(path).relative_to(PurePosixPath(root)))
    except ValueError:
        return None


def _place(doc2: dict, path: str, write: str | None) -> dict:
    """The connector that reaches `path` (the longest root that contains it) and the place on it."""
    best = None
    for cid, c in doc2["connectors"].items():
        rel = _relative(path, str(c.get("root") or ""))
        if rel is not None and (best is None or len(str(c.get("root"))) > len(str(doc2["connectors"][best[0]].get("root")))):
            best = (cid, rel)
    if best is None:                           # relative to the registry, or absolute on the machine: the server's directory
        cid = next((k for k, c in doc2["connectors"].items() if c.get("kind") == "directory" and not c.get("root")), None)
        if cid is None:
            raise RegistryError(f"no connector reaches {path} — add a directory connector with root \"\"")
        best = (cid, path)
    out = {"connector": best[0], "place": best[1]}
    if write:
        wr = str(doc2["connectors"][best[0]].get("write_root") or "")
        out["write_place"] = _relative(write, wr) or write
    return out


def canonical_applications(apps: dict) -> dict[str, str]:
    """Each application id → the one it stands for: entries over the same configuration are one application; the
    shortest id wins (`gatehouse-muster` → `gatehouse`). The others were samples filed as applications (ADR-032)."""
    by_dir: dict[str, list[str]] = {}
    for aid, a in apps.items():
        by_dir.setdefault(str(a.get("config_dir")), []).append(aid)
    out = {}
    for ids in by_dir.values():
        keep = sorted(ids, key=lambda x: (len(x), x))[0]
        for aid in ids:
            out[aid] = keep
    return out


def migrate(doc1: dict, plan: dict) -> dict:
    """Format 2 from a format-1 registry and a plan:

        {"connectors": {...},
         "workspaces": [{"id": "operations", "label": "Betrieb", "open": false, "members": [...], "instances": ["pressroom", …]}]}

    Every format-1 entry must be named in exactly one workspace. Paths, modes, data points and templates of every
    instance come out as they were (`check()` proves it); applications over the same configuration become one."""
    if is_v2(doc1):
        raise RegistryError("the registry is in format 2 already")
    entries = {str(w["id"]): w for w in doc1.get("workspaces") or []}
    named = [i for ws in plan.get("workspaces") or [] for i in ws.get("instances") or []]
    if sorted(named) != sorted(entries):
        missing, extra = set(entries) - set(named), set(named) - set(entries)
        dup = {i for i in named if named.count(i) > 1}
        raise RegistryError("the plan must name every entry once — " + "; ".join(x for x in (
            f"missing: {', '.join(sorted(missing))}" if missing else "", f"unknown: {', '.join(sorted(extra))}" if extra else "",
            f"twice: {', '.join(sorted(dup))}" if dup else "") if x))
    apps1 = doc1.get("applications") or {}
    canon = canonical_applications(apps1)
    doc2 = {"format": FORMAT, "$comment": COMMENT,
            "applications": {aid: copy.deepcopy(a) for aid, a in apps1.items() if canon[aid] == aid},
            "connectors": copy.deepcopy(plan.get("connectors") or {}), "workspaces": []}
    if "defaults" in doc1:
        doc2["defaults"] = copy.deepcopy(doc1["defaults"])
    for wp in plan.get("workspaces") or []:
        ws = {"id": wp["id"], "label": wp.get("label") or wp["id"], "open": bool(wp.get("open", False)),
              "members": list(wp.get("members") or []), "data_points": [], "instances": []}
        if wp.get("open_identity"):
            ws["open_identity"] = True
        for iid in wp.get("instances") or []:
            e = entries[iid]
            app = str(e["application"])
            seed = (apps1.get(app) or {}).get("template") if canon.get(app, app) != app else None
            inst = {"id": iid, "application": canon.get(app, app), "label": e.get("label") or iid, "mode": e.get("mode", "live")}
            for k in ("owner", "created", "cloned_from", "components"):
                if e.get(k):
                    inst[k] = e[k]
            if e.get("open_identity") and not wp.get("open_identity"):
                inst["open_identity"] = True
            if sorted(e.get("members") or []) != sorted(ws["members"]):
                inst["members"] = list(e.get("members") or [])
            if e.get("data_points"):
                home = f"{iid}-home"
                ws["data_points"].append({"name": home, **_place(doc2, str(e["root"]), e.get("write_root"))})
                cases = []
                for d in e["data_points"]:
                    name = f"{iid}-{d['name']}"
                    ws["data_points"].append({"name": name, **_place(doc2, str(d["root"]), d.get("write_root")),
                                              "readers": list(d.get("readers") or []), "writers": list(d.get("writers") or []),
                                              **({"label": d["label"]} if d.get("label") else {})})
                    cases.append({"point": name, "as": d["name"]})
                inst["bind"] = {"home": home, "cases": cases}
            else:
                p = {"name": iid, **_place(doc2, str(e["root"]), e.get("write_root"))}
                if seed:
                    p["seed"] = seed
                ws["data_points"].append(p)
                inst["bind"] = {"cases": iid}
            ws["instances"].append(inst)
        doc2["workspaces"].append(ws)
    return doc2


def _abs(base: Path, p: str | None) -> str | None:
    if not p:
        return None
    q = Path(p).expanduser()
    return str(q if q.is_absolute() else base / q)


def check(doc1: dict, doc2: dict, base: Path) -> list[str]:
    """What differs between a format-1 registry and its migration, per instance, beyond who may enter (that is the
    workspace's now). Empty = every instance reads and writes where it did, in the same mode, with the same template."""
    apps1 = doc1.get("applications") or {}
    canon = canonical_applications(apps1)
    new = {i["id"]: i for i in instances(doc2)}
    out = []
    for e in doc1.get("workspaces") or []:
        iid = str(e["id"])
        n = new.get(iid)
        if n is None:
            out.append(f"{iid}: missing")
            continue
        want_tpl = (apps1.get(str(e["application"])) or {}).get("template")
        got_tpl = n.get("template") or (doc2["applications"].get(n["application"]) or {}).get("template")
        pairs = [("root", _abs(base, e.get("root")), _abs(base, n.get("root"))),
                 ("write_root", _abs(base, e.get("write_root")), _abs(base, n.get("write_root"))),
                 ("mode", e.get("mode", "live"), n.get("mode")),
                 ("application", canon.get(str(e["application"])), n.get("application")),
                 ("config_dir", (apps1.get(str(e["application"])) or {}).get("config_dir"), (doc2["applications"].get(n["application"]) or {}).get("config_dir")),
                 ("template", want_tpl, got_tpl),
                 ("open_identity", bool(e.get("open_identity")), bool(n.get("open_identity"))),
                 ("data_points", [(d["name"], _abs(base, d["root"]), _abs(base, d.get("write_root")), sorted(d.get("readers") or []), sorted(d.get("writers") or []), d.get("label"))
                                  for d in e.get("data_points") or []],
                  [(d["name"], _abs(base, d["root"]), _abs(base, d.get("write_root")), sorted(d.get("readers") or []), sorted(d.get("writers") or []), d.get("label"))
                   for d in n.get("data_points") or []])]
        out += [f"{iid}: {k} {a!r} → {b!r}" for k, a, b in pairs if a != b]
    return out
