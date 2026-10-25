"""The surface: intro, sign-in, an overview of cards, one page per module.

Server-rendered. No build step. The only JavaScript is htmx, shipped as a
file, used for refreshing the grid in place — and a few lines for the intro.

Who is looking comes from a signed session cookie when users are configured;
their role and their context directory follow from that. Without users the
cockpit runs as the default role, and the role switch (off by default) is
the only way to look as somebody else — a deliberate choice for a private
machine, never for a shared one.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hmac
import json
import re
from urllib.parse import quote
import mimetypes
import secrets
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .access import Access, Denied
from .actions import Actions
from .audit import AuditLog
from .config import Config
from .detail import blocks_for, document_for
from .i18n import I18n
from .registry import build_cards, card_for, mount_apps, plugins_for, reader_for
from .setup import add_attribute, schemas_for
from .users import User, Users
from .account import AccountError, Accounts, SECRETS, SETTINGS
from .workspaces import WorkspaceError, Workspaces, mount_all, mount_one, web_dist_default

HERE = Path(__file__).parent


def create_app(config: Config) -> FastAPI:
    # The API description is served by a route of our own, behind the same gate as the pages.
    app = FastAPI(title=config.name, version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    from .detail import render_md_safe
    templates.env.filters["md"] = render_md_safe       # an agent's answer is Markdown; shown rendered, raw HTML as text

    # Served under a prefix ("/test"), every link and redirect carries it; at the root it is empty.
    # Templates write `{{ base }}/m/…`; the code goes through `go()` and `route_path()`.
    base = config.base_path
    cookie_path = base or "/"               # one sign-in per stage: a cookie never leaks into the neighbour's prefix

    def go(path: str) -> RedirectResponse:
        return RedirectResponse(base + path, status_code=303)

    def route_path(request: Request) -> str:
        """The path inside this instance — the prefix removed, when there is one."""
        p = request.url.path
        return p[len(base):] if base and p.startswith(base) else p

    i18n = I18n(HERE / "locales")
    for plugin in plugins_for(config).values():          # a plugin may bring its own strings
        if plugin.locales and plugin.locales.is_dir():
            i18n.merge(plugin.locales)
    audit = AuditLog(config.audit_path)
    users = Users(config.users_path, config.secret_path)
    accounts = Accounts(config.accounts_path)
    ws_error = None
    try:
        workspaces = Workspaces(config.workspaces_path, config.workspaces_path.parent)
    except WorkspaceError as exc:                       # a broken registry is a line on the dashboard, not a shell that will not start
        workspaces, ws_error = None, str(exc)
    web_dist = config.casefile_web or web_dist_default()

    def identity(request: Request) -> str | None:
        """Who is signed in to the cockpit — the identity every mounted workspace works with."""
        return users.redeem(request.cookies.get("session"))

    if base:
        # Readers, Markdown and templates all write root-relative paths ("/m/pipeline/…"); nobody downstream
        # knows about the prefix. It is added here, once, on every HTML page that leaves — the one place that
        # knows where this instance is served. Media and JSON pass untouched.
        _ATTR = re.compile(rb'((?:\s(?:href|src|action|hx-get|hx-post|poster)=")|location\.href=\')/(?!/)')
        _prefix = base.encode()

        @app.middleware("http")
        async def prefix_links(request: Request, call_next):
            response = await call_next(request)
            if not response.headers.get("content-type", "").startswith("text/html"):
                return response
            parts = route_path(request).split("/")
            if (len(parts) >= 3 and parts[1] == "w") or (len(parts) >= 4 and parts[1] == "m" and parts[3] == "app"):
                return response                       # mounted apps build their links from root_path themselves — prefixing twice would break them
            body = b"".join([chunk async for chunk in response.body_iterator])
            body = _ATTR.sub(lambda m: m.group(1) + _prefix + b"/", body)
            headers = dict(response.headers)
            headers["content-length"] = str(len(body))
            return Response(body, status_code=response.status_code, headers=headers, media_type=response.media_type)

    # ------------------------------------------------------------- identity
    def csrf_token(request: Request) -> str:
        """One token per browser, in a cookie; every POST form carries it as a field.

        The middleware below decides the token for this request before any page
        renders, so the field in the form and the cookie on the response agree.
        """
        return getattr(request.state, "csrf", None) or request.cookies.get("csrf") or ""

    def back_to(form: dict) -> str | None:
        """A page inside the cockpit the form asks to return to — never an outside URL."""
        b = (form.get("_back") or "").strip()
        return base + b if b.startswith("/m/") and "://" not in b and not b.startswith("//") else None

    def csrf_ok(request: Request, form: dict) -> bool:
        cookie = request.cookies.get("csrf")
        return bool(cookie) and hmac.compare_digest(cookie, form.get("_csrf", ""))

    def client_ip(request: Request) -> str:
        # Behind the reverse proxy uvicorn rewrites request.client from X-Forwarded-For (--proxy-headers).
        return request.client.host if request.client else "?"

    def set_cookie(resp, key, value, **kw):
        resp.set_cookie(key, value, secure=config.secure_cookies, path=cookie_path, **kw)

    def who(request: Request) -> User | None:
        name = users.redeem(request.cookies.get("session"))
        return users.get(name, config.base_dir) if name else None

    def person_name(access: Access, role, login: str) -> str | None:
        """The name people.json gives the signed-in id, read through access like everything else."""
        try:
            people = access.read_json(config.people[0], config.people[1], role).get("people", [])
            return next((x["name"] for x in people if x["id"] == login), None)
        except Exception:
            return None

    def ctx(request: Request) -> dict:
        lang = i18n.pick(request.cookies.get("lang"), config.locale)
        user = who(request)
        if user:
            role = config.roles.get(user.role) or config.role()
            variables = user.as_vars()
        else:
            role_id = request.cookies.get("role") if config.role_switch else None
            role = config.role(role_id if role_id in config.roles else None)
            variables = {}
        access = Access(config, audit, variables)
        if user and config.people:
            user = dataclasses.replace(user, display=person_name(access, role, user.name) or user.display)
        return {
            "request": request, "config": config, "lang": lang, "languages": i18n.languages(),
            "user": user, "role": role,
            "roles": list(config.roles) if config.role_switch and not user else [],
            "t": lambda key, **kw: i18n.t(lang, key, **kw),
            "version": __version__, "export": False,
            "modules_by_id": {m.id: m for m in config.modules},
            "nav_modules": [m for m in config.modules if m.enabled and role.may_open(m.id)],
            "plugins": plugins_for(config),
            "current": route_path(request).split("/")[2] if route_path(request).startswith("/m/") else "",
            "route": route_path(request),
            "now": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
            "_access": access,
            "_actions": Actions(config, access, audit, plugins_for(config)),
            "csrf": csrf_token(request),
            "view": "werkstatt" if request.cookies.get("view") == "werkstatt" else "desk",
            "workspaces": workspaces.for_user(user.name) if (workspaces and user) else (workspaces.for_user(None) if workspaces else []),
            "applications": workspaces.applications if workspaces else {},
            **nav_state(user, role),
            "ws_error": ws_error,
            "ws_failures": getattr(app.state, "workspace_failures", {}),
        }

    stage = (config.environment or "prod").lower()
    from .agents import Catalog

    def templates_now():
        return Catalog.load(config.agents_path)

    def team_of(user):
        return accounts.team(user.name, templates_now(), stage)

    def store_of(user):
        return accounts.store(user.name, stage)

    def nav_state(user, role) -> dict:
        """The side panel's first view and the bell: this person's agents, and their running sessions — answered or
        still thinking. A broken team costs the panel, never the page."""
        agents, notes = [], []
        if not user:
            return {"team": agents, "notes": notes}
        try:
            team, store = team_of(user), store_of(user)
            running = {}
            for s in store.active():
                running.setdefault(s.agent, s.id)
                turns = store.transcript(s.id)
                kind = "thinking" if store.pending(s.id) else ("answered" if turns and turns[-1]["role"] != "user" else "open")
                a = team.get(s.agent)
                notes.append({"session": s.id, "topic": s.topic, "kind": kind, "agent": a.label if a else s.agent, "agent_id": s.agent,
                              "initials": a.initials if a else s.agent[:2].upper(), "place": s.place})
            agents = [{"id": a.id, "label": a.label, "initials": a.initials, "img": a.avatar_path is not None,
                       "running": a.id in running} for a in team.agents.values()]
        except Exception:                                # noqa: BLE001
            pass
        return {"team": agents, "notes": notes}

    def gate(request: Request):
        """Redirect to the intro or the sign-in when users exist and nobody is signed in."""
        if config.login_required and who(request) is None:
            seen = request.cookies.get("intro") == "1"
            return go("/login" if seen else "/intro")
        return None

    # ---------------------------------------------------------------- account and workspaces
    @app.get("/account", response_class=HTMLResponse)
    def account_page(request: Request, ok: str | None = None, err: str | None = None):
        if (r := gate(request)):
            return r
        c = ctx(request)
        if not c["user"]:
            return go("/")
        return templates.TemplateResponse(request, "account.html", {**c, "status": accounts.status(c["user"].name), "ok": ok, "err": err,
                                                                     "billing_modes": SETTINGS["billing"], "secret_keys": list(SECRETS)})

    @app.post("/account", response_class=HTMLResponse)
    async def account_post(request: Request):
        if (r := gate(request)):
            return r
        c = ctx(request)
        form = {k: str(v) for k, v in (await request.form()).items()}
        if not c["user"] or not csrf_ok(request, form):
            return go("/account?err=" + quote("the form token did not match — reload the page and try again"))
        name, what = c["user"].name, form.get("what", "")
        try:
            if what == "setting":
                accounts.set(name, form.get("key", ""), form.get("value", ""))
                msg = f"{form.get('key')} = {form.get('value')}"
            elif what == "secret":
                accounts.set_secret(name, form.get("key", ""), form.get("value", ""))
                msg = f"{form.get('key')} set"
            elif what == "clear":
                accounts.clear_secret(name, form.get("key", ""))
                msg = f"{form.get('key')} cleared"
            else:
                raise AccountError("unknown form")
        except AccountError as exc:
            return go("/account?err=" + quote(str(exc)))
        return go("/account?ok=" + quote(msg))

    @app.get("/workspaces/new", response_class=HTMLResponse)
    def workspace_new(request: Request, err: str | None = None):
        if (r := gate(request)):
            return r
        c = ctx(request)
        if not c["user"] or workspaces is None:
            return go("/")
        return templates.TemplateResponse(request, "workspace_new.html", {**c, "err": err, "sources": workspaces.for_user(c["user"].name),
                                                                           "may_share": c["role"].may_act("*") or c["role"].may_act("workspaces.shared")})

    @app.post("/workspaces/new", response_class=HTMLResponse)
    async def workspace_create(request: Request):
        if (r := gate(request)):
            return r
        c = ctx(request)
        form = {k: str(v) for k, v in (await request.form()).items()}
        if not c["user"] or workspaces is None or not csrf_ok(request, form):
            return go("/workspaces/new?err=" + quote("the form token did not match — reload the page and try again"))
        shared = form.get("shared") == "1" and (c["role"].may_act("*") or c["role"].may_act("workspaces.shared"))
        w = None
        try:
            w = workspaces.create(form.get("id", "").strip().lower(), form.get("application", ""), None if shared else c["user"].name,
                                  label=form.get("label", "").strip(), source=form.get("source") or None, shared=shared)
            mount_one(app, workspaces, w, identity, users.secret_text(), web_dist, config.environment, (base or "") + "/")
        except WorkspaceError as exc:
            return go("/workspaces/new?err=" + quote(str(exc)))
        except Exception as exc:                        # noqa: BLE001 — the entry stands, the mount did not come up: say so
            return go("/?err=" + quote(f"{w.id if w else '?'}: {type(exc).__name__}: {exc}"))
        return go(f"/w/{w.id}/")

    # ---------------------------------------------------------------- the person's team and sessions (ADR-020)
    def api_csrf_ok(request: Request) -> bool:
        cookie = request.cookies.get("csrf")
        return bool(cookie) and hmac.compare_digest(cookie, request.headers.get("x-csrf", ""))

    def place_for(user, raw: dict) -> dict:
        """The place the panel reports, kept only where the person may be: a workspace they cannot open is dropped."""
        from .sessions import clean_place
        place = clean_place(raw)
        if place.get("workspace") and (workspaces is None or not workspaces.may_open(user.name, place["workspace"])):
            place.pop("workspace")
        return place

    def turn_view(t: dict) -> dict:
        from .detail import render_md_safe
        out = {k: t.get(k) for k in ("at", "role", "model", "cost_usd")}
        out["html"] = render_md_safe(t["text"]) if t["role"] == "assistant" else None
        out["text"] = t["text"]
        return out

    def session_view(store, team, s) -> dict:
        a = team.get(s.agent)
        p = store.pending(s.id)
        return {"id": s.id, "agent": s.agent, "label": a.label if a else s.agent, "initials": a.initials if a else "?",
                "img": bool(a and a.avatar_path), "topic": s.topic, "status": s.status, "started": s.started, "place": s.place,
                "pending": (p or {}).get("type"), "turns": [turn_view(t) for t in store.transcript(s.id)],
                "log": Path(s.log).name if s.log else None}

    @app.get("/team", response_class=HTMLResponse)
    def team_page(request: Request, ok: str | None = None, err: str | None = None):
        if (r := gate(request)):
            return r
        c = ctx(request)
        if not c["user"]:
            return go("/")
        team = team_of(c["user"])
        store = store_of(c["user"])
        return templates.TemplateResponse(request, "team.html", {
            **c, "ok": ok, "err": err, "members": list(team.agents.values()), "problems": team.problems,
            "hireable": [t for t in team.hireable(c["role"].id) if t.id not in team.agents],
            "logs_dir": accounts.settings(c["user"].name).get("logs_dir", ""), "logs_now": store.log_dir or store.dir / "logs",
            "active": store.active(), "closed": list(reversed(store.closed()))[:15], "stage": stage,
            "templates_missing": config.agents_path is None})

    @app.post("/team", response_class=HTMLResponse)
    async def team_post(request: Request):
        if (r := gate(request)):
            return r
        c = ctx(request)
        form = {k: str(v) for k, v in (await request.form()).items()}
        if not c["user"] or not csrf_ok(request, form):
            return go("/team?err=" + quote("the form token did not match — reload the page and try again"))
        from .agents import AgentError
        from .account import AccountError
        team = team_of(c["user"])
        try:
            what = form.get("what")
            if what == "hire":
                a = team.hire(form.get("template", ""), (form.get("id") or "").strip().lower() or None, role=c["role"].id,
                              model=form.get("model", "").strip() or None)
                audit.record(c["user"].name, "team", a.id, "agent.hire")
                return go("/team?ok=" + quote(f"{a.label} is on your team"))
            if what == "dismiss":
                if team.dismiss(form.get("agent", "")):
                    audit.record(c["user"].name, "team", form.get("agent", ""), "agent.dismiss")
                return go("/team?ok=" + quote("dismissed — the memory is kept in your account"))
            if what == "logs_dir":
                accounts.set(c["user"].name, "logs_dir", form.get("logs_dir", ""))
                return go("/team?ok=" + quote("saved"))
        except (AgentError, AccountError) as exc:
            return go("/team?err=" + quote(str(exc)))
        return go("/team")

    @app.get("/sessions/{sid}", response_class=HTMLResponse)
    def session_page(request: Request, sid: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        if not c["user"]:
            return go("/")
        from .sessions import SessionError
        store, team = store_of(c["user"]), team_of(c["user"])
        try:
            s = store.get(sid)
        except SessionError:
            s = None
        if s is None:
            return go("/team?err=" + quote("no such session of yours"))
        log_text = Path(s.log).read_text(encoding="utf-8") if s.log and Path(s.log).is_file() else None
        return templates.TemplateResponse(request, "session.html", {**c, "v": session_view(store, team, s), "log_text": log_text})

    @app.get("/api/team")
    def api_team(request: Request):
        c = ctx(request)
        if not c["user"]:
            return JSONResponse({"reason": "not signed in"}, status_code=401)
        st = nav_state(c["user"], c["role"])
        return JSONResponse({"agents": st["team"], "sessions": st["notes"], "csrf": csrf_token(request)})

    @app.post("/api/sessions")
    async def api_start(request: Request):
        c = ctx(request)
        if not c["user"] or not api_csrf_ok(request):
            return JSONResponse({"reason": "not signed in, or the page is stale — reload it"}, status_code=403)
        from .sessions import SessionError
        body = await request.json()
        team = team_of(c["user"])
        a = team.get(str(body.get("agent", "")))
        if a is None:
            return JSONResponse({"reason": "this agent is not on your team"}, status_code=400)
        try:
            s, overlapping = store_of(c["user"]).start(a.id, c["user"].name, str(body.get("topic", "")), place_for(c["user"], body.get("place") or {}))
        except SessionError as exc:
            return JSONResponse({"reason": str(exc)}, status_code=400)
        audit.record(c["user"].name, "team", s.id, "agent-session.start")
        return JSONResponse({"id": s.id, "overlapping": [o.id for o in overlapping]})

    @app.get("/api/sessions/{sid}")
    def api_session(request: Request, sid: str):
        c = ctx(request)
        if not c["user"]:
            return JSONResponse({"reason": "not signed in"}, status_code=401)
        from .sessions import SessionError
        store = store_of(c["user"])
        try:
            s = store.get(sid)
        except SessionError:
            s = None
        if s is None:
            return JSONResponse({"reason": "no such session of yours"}, status_code=404)
        return JSONResponse(session_view(store, team_of(c["user"]), s))

    @app.post("/api/sessions/{sid}/{what}")
    async def api_act(request: Request, sid: str, what: str):
        c = ctx(request)
        if not c["user"] or not api_csrf_ok(request):
            return JSONResponse({"reason": "not signed in, or the page is stale — reload it"}, status_code=403)
        from .sessions import SessionError
        body = await request.json()
        store = store_of(c["user"])
        try:
            if what == "say":
                store.say(sid, c["user"].name, str(body.get("text", "")))
            elif what == "end":
                store.end(sid, c["user"].name, str(body.get("note", "")))
                audit.record(c["user"].name, "team", sid, "agent-session.end")
            else:
                return JSONResponse({"reason": f"'{what}' is not an action"}, status_code=404)
        except SessionError as exc:
            return JSONResponse({"reason": str(exc)}, status_code=400)
        return JSONResponse({"ok": True})

    @app.get("/api/agents/{aid}/avatar")
    def agent_avatar(request: Request, aid: str):
        c = ctx(request)
        a = team_of(c["user"]).get(aid) if c["user"] else None
        if a is None or a.avatar_path is None:
            return Response(status_code=404)
        try:
            thumb = a.thumbnail(config.accounts_path.parent / "cache" / "avatars")
        except Exception:                                # noqa: BLE001 — a picture Pillow cannot read is served as it is
            thumb = None
        return FileResponse(thumb or a.avatar_path, media_type="image/webp" if thumb else None,
                            headers={"Cache-Control": "private, max-age=86400"})

    # ---------------------------------------------------------------- entry
    @app.get("/intro", response_class=HTMLResponse)
    def intro(request: Request):
        return templates.TemplateResponse(request, "intro.html", ctx(request))

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, failed: int = 0):
        if who(request):
            return go("/")
        c = ctx(request)
        c["failed"], c["locked"] = bool(failed), failed == 2
        resp = templates.TemplateResponse(request, "login.html", c)
        set_cookie(resp, "intro", "1", samesite="lax", max_age=30 * 24 * 3600)
        return resp

    @app.post("/login")
    async def login(request: Request):
        form = {k: str(v) for k, v in (await request.form()).items()}
        name, password = form.get("name", "").strip(), form.get("password", "")
        ip = client_ip(request)
        if not csrf_ok(request, form):
            return go("/login?failed=1")
        if (until := users.locked_until(name)):
            audit.record(name or "?", "cockpit", "session", "login", ok=False,
                         reason=f"locked for {int(until - time.time()) // 60 + 1} min", ip=ip)
            return go("/login?failed=2")
        if users.verify(name, password):
            users.clear_failures(name)
            audit.record(name, "cockpit", "session", "login", ip=ip)
            resp = go("/")
            set_cookie(resp, "session", users.issue(name), httponly=True, samesite="lax")
            return resp
        users.note_failure(name, config.lockout_after, config.lockout_minutes)
        audit.record(name or "?", "cockpit", "session", "login", ok=False, reason="bad credentials", ip=ip)
        return go("/login?failed=1")

    @app.get("/logout")
    def logout(request: Request):
        u = who(request)
        if u:
            audit.record(u.name, "cockpit", "session", "logout")
        resp = go("/login")
        resp.delete_cookie("session", path=cookie_path)
        return resp

    # ---------------------------------------------------------------- pages
    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request, err: str | None = None):
        if (r := gate(request)):
            return r
        c = ctx(request)
        # The dashboard is where one lands (Chris, 2026-10-24): workspaces first, then the workshop modules. `home` in the
        # config still names the module the pipeline link points at, but nobody is forwarded past the dashboard any more.
        c["cards"] = build_cards(config, c["_access"], c["role"])
        c["err"] = err
        return templates.TemplateResponse(request, "index.html", c)

    @app.get("/grid", response_class=HTMLResponse)
    def grid(request: Request):
        if (r := gate(request)):
            return r
        c = ctx(request)
        c["cards"] = build_cards(config, c["_access"], c["role"])
        return templates.TemplateResponse(request, "grid.html", c)

    def _with_words(t, words: dict):
        """The pipeline's vocabulary.json may say its own words for the desk's locale keys ("words": {key: text}).
        A claims file calls a piece a case; the locale stays the fallback."""
        if not words:
            return t
        def tt(key, **kw):
            w = words.get(key)
            return (w.format(**kw) if kw else w) if isinstance(w, str) else t(key, **kw)
        return tt

    def desk_page(request: Request, c: dict, module, flash=None, flash_ok=True):
        """The creator's start page: pieces by what is next. Only a plugin that offers `desk` has one."""
        reader = reader_for(module, config)
        fn = getattr(reader, "desk", None)
        if fn is None:
            return None
        try:
            desk = fn(c["_access"], c["role"], module, config, viewer=c["user"].display if c["user"] else None, lang=c["lang"])
        except Denied as exc:
            desk = {"groups": [], "error": str(exc)}
        except Exception as exc:
            desk = {"groups": [], "error": f"{type(exc).__name__}: {exc}"}
        c["module"], c["desk"], c["flash"], c["flash_ok"] = module, desk, flash, flash_ok
        c["t"] = _with_words(c["t"], desk.get("words") or {})
        c["plugin"] = plugins_for(config).get(module.plugin)
        c["options"] = c["_actions"].options_for(module, c["role"])
        return templates.TemplateResponse(request, "desk.html", c)

    def piece_page(request: Request, c: dict, module, ref: str, outcome=None, ran=None):
        """One piece the creator's way. None when the plugin has no `piece` or the ref is not a piece."""
        reader = reader_for(module, config)
        fn = getattr(reader, "piece", None)
        if fn is None:
            return None
        try:
            piece = fn(c["_access"], c["role"], module, config, ref, viewer=c["user"].display if c["user"] else None, lang=c["lang"])
        except Denied as exc:
            piece = {"ref": ref, "title": ref, "error": str(exc), "files": [], "notes": [], "helpers": [], "runs": [], "open_for_me": []}
        if piece is None:
            return None
        if piece.get("draft") and piece["draft"].get("text") is not None:
            from .detail import render_md_safe
            d = piece["draft"]
            d["html"] = render_md_safe(d["text"]) if d.get("kind") == "md" else "<pre class='plain'>" + d["text"].replace("&", "&amp;").replace("<", "&lt;") + "</pre>"
        c["module"], c["piece"], c["outcome"], c["ran"] = module, piece, outcome, ran
        c["t"] = _with_words(c["t"], (piece.get("words") or {}).get("ui") or {})
        c["options"] = c["_actions"].options_for(module, c["role"])
        c["flash"] = request.query_params.get("msg")
        c["flash_ok"] = request.query_params.get("ok") != "0"
        return templates.TemplateResponse(request, "piece.html", c)

    def module_page(request: Request, c: dict, module, outcome=None, ran=None):
        card = card_for(config, c["_access"], c["role"], module.id)
        c["card_"], c["module"] = card, module
        c["raw"] = json.dumps(card.panel, ensure_ascii=False, indent=2) if card and card.panel else ""
        c["outcome"], c["ran"] = outcome, ran
        c["options"] = c["_actions"].options_for(module, c["role"])
        c["plugin"] = plugins_for(config).get(module.plugin)
        c["has_desk"] = getattr(reader_for(module, config), "desk", None) is not None
        try:
            c["blocks"] = (blocks_for(reader_for(module, config), c["_access"], c["role"], module, config)
                           if card and card.shown else [])
        except Exception as exc:
            c["blocks"] = [{"kind": "document", "html": f"<p class='hint'>{type(exc).__name__}: {exc}</p>"}]
        c["app_error"] = app.state.app_failures.get(module.id)
        return templates.TemplateResponse(request, "module.html", c)

    def find_module(module_id: str):
        return next((m for m in config.modules if m.id == module_id and m.enabled), None)

    @app.get("/m/{module_id}", response_class=HTMLResponse)
    def module(request: Request, module_id: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        module = find_module(module_id)
        if module is None or not c["role"].may_open(module_id):
            return go("/")
        if c["view"] == "desk" and (r := desk_page(request, c, module, flash=request.query_params.get("msg"), flash_ok=request.query_params.get("ok") != "0")):
            return r
        return module_page(request, c, module)

    async def read_form(request: Request, action=None) -> tuple[dict, list[Path]]:
        """Form values as strings. A file field becomes a temp path plus '<name>.name' with its original name.

        Size is enforced while reading, so an oversized upload is refused before
        it is written in full. The temp files are removed by the caller.
        """
        limit = config.max_upload_mb * 1024 * 1024
        form, temps = {}, []
        for k, v in (await request.form()).items():
            if hasattr(v, "filename"):                     # starlette UploadFile
                if not v.filename:
                    form[k] = ""
                    continue
                fd, tmp = tempfile.mkstemp(prefix="cockpit-upload-", dir=None)
                size = 0
                with open(fd, "wb") as out:
                    while chunk := await v.read(1024 * 1024):
                        size += len(chunk)
                        if size > limit:
                            out.close()
                            Path(tmp).unlink(missing_ok=True)
                            raise Denied(f"'{v.filename}' is larger than {config.max_upload_mb} MB")
                        out.write(chunk)
                temps.append(Path(tmp))
                form[k] = tmp
                form[k + ".name"] = Path(v.filename).name
            else:
                form[k] = str(v)
        return form, temps

    @app.post("/m/{module_id}/a/{action_id}", response_class=HTMLResponse)
    async def act(request: Request, module_id: str, action_id: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        module = find_module(module_id)
        action = c["_actions"].find(module, action_id) if module else None
        if module is None or action is None:
            return go("/")
        temps: list[Path] = []
        try:
            form, temps = await read_form(request)
            if not csrf_ok(request, form):
                raise Denied("the form token did not match — reload the page and try again")
            outcome = c["_actions"].run(module, action, form, c["role"], user=c["user"].name if c["user"] else None)
            if (back := back_to(form)) and outcome.ok:
                return RedirectResponse(back + ("&" if "?" in back else "?") + "ok=1&msg=" + quote(outcome.output.strip()[-200:]), status_code=303)
            if back and c["view"] == "desk" and (r := desk_page(request, c, module, flash=outcome.output.strip()[-300:], flash_ok=False)):
                return r                                      # refused: the page the form sits on, the form open, the reason in red
        except Denied as exc:
            outcome = type("O", (), {"ok": False, "output": str(exc), "argv": []})()
        finally:
            for t in temps:
                t.unlink(missing_ok=True)
        return module_page(request, c, module, outcome, action)

    @app.get("/m/{module_id}/doc/{ref:path}", response_class=HTMLResponse)
    def document(request: Request, module_id: str, ref: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        module = find_module(module_id)
        if module is None or not c["role"].may_open(module_id):
            return go("/")
        if c["view"] == "desk" and (r := piece_page(request, c, module, ref)):
            return r
        try:
            doc = document_for(reader_for(module, config), c["_access"], c["role"], module, config, ref)
        except Denied as exc:
            doc = {"title": ref, "html": f"<p class='hint'>{exc}</p>", "ref": ref}
        if doc is None:
            return go(f"/m/{module_id}")
        c["module"], c["doc"] = module, doc
        c["outcome"], c["ran"] = None, None
        c["has_desk"] = getattr(reader_for(module, config), "piece", None) is not None
        c["options"] = c["_actions"].options_for(module, c["role"])
        return templates.TemplateResponse(request, "document.html", c)

    @app.post("/m/{module_id}/doc/{ref:path}/a/{action_id}", response_class=HTMLResponse)
    async def act_on_document(request: Request, module_id: str, ref: str, action_id: str):
        """A document-scoped action: the tool gets {ref}, and the page shows the result on the document."""
        if (r := gate(request)):
            return r
        c = ctx(request)
        module = find_module(module_id)
        action = c["_actions"].find(module, action_id) if module else None
        if module is None or action is None or action.scope != "document":
            return go("/")
        temps: list[Path] = []
        try:
            form, temps = await read_form(request)
            if not csrf_ok(request, form):
                raise Denied("the form token did not match — reload the page and try again")
            outcome = c["_actions"].run(module, action, form, c["role"], ref=ref,
                                        user=c["user"].name if c["user"] else None)
        except Denied as exc:
            outcome = type("O", (), {"ok": False, "output": str(exc), "argv": []})()
        finally:
            for t in temps:
                t.unlink(missing_ok=True)
        if c["view"] == "desk" and (r := piece_page(request, c, module, ref, outcome=outcome, ran=action)):
            return r
        try:
            doc = document_for(reader_for(module, config), c["_access"], c["role"], module, config, ref)
        except Denied as exc:
            doc = {"title": ref, "html": f"<p class='hint'>{exc}</p>", "ref": ref}
        c["module"], c["doc"] = module, doc or {"title": ref, "html": "", "ref": ref}
        c["outcome"], c["ran"] = outcome, action
        c["options"] = c["_actions"].options_for(module, c["role"])
        return templates.TemplateResponse(request, "document.html", c)

    @app.get("/m/{module_id}/file/{ref:path}")
    def file(request: Request, module_id: str, ref: str):
        """An image or a video out of a released source — through access.resolve, like every read.

        Only media types are served; a text file has its document route, and
        anything else is not for the browser. The response is served inline
        with the type the extension says, never sniffed.
        """
        if (r := gate(request)):
            return r
        c = ctx(request)
        module = find_module(module_id)
        if module is None or not c["role"].may_open(module_id) or not module.sources:
            return go("/")
        media, _ = mimetypes.guess_type(ref)
        if not media or not (media.startswith(("image/", "video/")) or media == "application/pdf"):
            return JSONResponse({"detail": "not a media file"}, status_code=404)
        try:
            path = c["_access"].resolve(module.sources[0], ref, c["role"])
        except Denied as exc:
            return JSONResponse({"detail": str(exc)}, status_code=404)
        return FileResponse(path, media_type=media, headers={"Content-Disposition": "inline",
                                                             "X-Content-Type-Options": "nosniff"})

    # ---------------------------------------------------------------- setup
    def setup_page(request: Request, c: dict, outcome=None):
        c["plugins"] = plugins_for(config)
        used: dict[str, list[str]] = {}
        for m in config.modules:
            used.setdefault(m.plugin, []).append(m.id)
        c["modules_using"] = used
        c["schemas"] = schemas_for(config, c["_access"], c["role"])
        c["outcome"] = outcome
        return templates.TemplateResponse(request, "setup.html", c)

    @app.get("/setup", response_class=HTMLResponse)
    def setup(request: Request):
        if (r := gate(request)):
            return r
        c = ctx(request)
        if not c["role"].may_act("setup.view") and not c["role"].may_act("*"):
            return go("/")
        return setup_page(request, c)

    @app.post("/setup/schema/{schema_id:path}/add", response_class=HTMLResponse)
    async def setup_schema_add(request: Request, schema_id: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        form = {k: str(v) for k, v in (await request.form()).items()}
        if not c["role"].may_act("setup.schema_add") and not c["role"].may_act("*"):
            return go("/")
        if not csrf_ok(request, form):
            ok, out = False, "the form token did not match — reload the page and try again"
        else:
            ok, out = add_attribute(config, c["_access"], c["role"], schema_id, form)
        return setup_page(request, c, type("O", (), {"ok": ok, "output": out})())

    @app.get("/set")
    def set_prefs(request: Request, lang: str | None = None, role: str | None = None, view: str | None = None):
        back = request.headers.get("referer", "/")
        resp = RedirectResponse(back, status_code=303)
        if lang and i18n.has(lang):
            set_cookie(resp, "lang", lang, samesite="lax", max_age=365 * 24 * 3600)
        if role and config.role_switch and role in config.roles and who(request) is None:
            set_cookie(resp, "role", role, samesite="lax")
        if view in ("desk", "werkstatt"):
            set_cookie(resp, "view", view, samesite="lax", max_age=365 * 24 * 3600)
        return resp

    @app.get("/api/panels")
    def api_panels(request: Request):
        if config.login_required and who(request) is None:
            return JSONResponse({"detail": "sign in first"}, status_code=401)
        c = ctx(request)
        return JSONResponse([{"module": card.module_id, "verdict": card.verdict,
                              "reason": card.reason, "panel": card.panel}
                             for card in build_cards(config, c["_access"], c["role"])])

    @app.get("/openapi.json")
    def openapi_json(request: Request):
        if config.login_required and who(request) is None:
            return JSONResponse({"detail": "sign in first"}, status_code=401)
        return JSONResponse(app.openapi())

    @app.get("/docs", response_class=HTMLResponse)
    def docs(request: Request):
        if (r := gate(request)):
            return r
        from fastapi.openapi.docs import get_swagger_ui_html
        return get_swagger_ui_html(openapi_url=base + "/openapi.json", title=f"{config.name} — API")

    # The contracts, once, in the same document that describes the routes.
    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        comps = schema.setdefault("components", {}).setdefault("schemas", {})
        for name in ("panel", "detail", "plugin"):
            comps[name.capitalize()] = json.loads((HERE / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
        app.openapi_schema = schema
        return schema
    app.openapi = openapi

    @app.middleware("http")
    async def csrf_cookie(request: Request, call_next):
        token = request.cookies.get("csrf") or secrets.token_urlsafe(24)
        request.state.csrf = token
        response = await call_next(request)
        if "csrf" not in request.cookies and response.headers.get("content-type", "").startswith("text/html"):
            response.set_cookie("csrf", token, samesite="strict", httponly=False, secure=config.secure_cookies, path=cookie_path)
        return response

    # Mounted plugin apps and workspaces sit behind the same gate and the same role check as the pages.
    _PANEL = ('<link rel="stylesheet" href="{b}/static/agent-panel.css"><script src="{b}/static/agent-panel.js" defer></script>'
              .format(b=base or "").encode())

    @app.middleware("http")
    async def panel_in_apps(request: Request, call_next):
        """The person's team stands beside them inside the mounted applications too (ADR-020): every HTML page under
        /w/<id>/ gets the side panel, once, before </body>. The application itself knows nothing of it."""
        response = await call_next(request)
        parts = route_path(request).split("/")
        if len(parts) < 3 or parts[1] != "w" or not response.headers.get("content-type", "").startswith("text/html") or who(request) is None:
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        if b"agent-panel.js" not in body:
            body = body.replace(b"</body>", _PANEL + b"</body>", 1)
        headers = dict(response.headers)
        headers["content-length"] = str(len(body))
        return Response(body, status_code=response.status_code, headers=headers, media_type=response.media_type)

    @app.middleware("http")
    async def guard_apps(request: Request, call_next):
        parts = route_path(request).split("/")
        if len(parts) >= 4 and parts[1] == "m" and parts[3] == "app":
            if config.login_required and who(request) is None:
                return go("/login")
            if not ctx(request)["role"].may_open(parts[2]):
                return go("/")
        if len(parts) >= 3 and parts[1] == "w":
            name = identity(request)
            is_api = len(parts) >= 4 and parts[3] == "api"
            if config.login_required and name is None:
                return JSONResponse({"reason": "not signed in to the cockpit"}, status_code=401) if is_api else go("/login")
            if workspaces is None or not workspaces.may_open(name, parts[2]):
                return JSONResponse({"reason": "no such workspace"}, status_code=404) if is_api else go("/")
        return await call_next(request)

    app.state.app_failures = dict(mount_apps(app, config))
    app.state.workspace_failures = mount_all(app, workspaces, identity, users.secret_text(), web_dist, config.environment, (base or "") + "/") if workspaces else {}
    app.state.workspaces = workspaces
    app.state.i18n = i18n
    app.state.users = users
    return app
