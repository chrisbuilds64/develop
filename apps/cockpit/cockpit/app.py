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

import datetime as dt
import hmac
import json
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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

HERE = Path(__file__).parent


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title=config.name, version=__version__, docs_url="/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")

    i18n = I18n(HERE / "locales")
    for plugin in plugins_for(config).values():          # a plugin may bring its own strings
        if plugin.locales and plugin.locales.is_dir():
            i18n.merge(plugin.locales)
    audit = AuditLog(config.audit_path)
    users = Users(config.users_path, config.secret_path)

    # ------------------------------------------------------------- identity
    def csrf_token(request: Request) -> str:
        """One token per browser, in a cookie; every POST form carries it as a field.

        The middleware below decides the token for this request before any page
        renders, so the field in the form and the cookie on the response agree.
        """
        return getattr(request.state, "csrf", None) or request.cookies.get("csrf") or ""

    def csrf_ok(request: Request, form: dict) -> bool:
        cookie = request.cookies.get("csrf")
        return bool(cookie) and hmac.compare_digest(cookie, form.get("_csrf", ""))

    def who(request: Request) -> User | None:
        name = users.redeem(request.cookies.get("session"))
        return users.get(name, config.base_dir) if name else None

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
        return {
            "request": request, "config": config, "lang": lang, "languages": i18n.languages(),
            "user": user, "role": role,
            "roles": list(config.roles) if config.role_switch and not user else [],
            "t": lambda key, **kw: i18n.t(lang, key, **kw),
            "version": __version__, "export": False,
            "modules_by_id": {m.id: m for m in config.modules},
            "now": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
            "_access": access,
            "_actions": Actions(config, access, audit, plugins_for(config)),
            "csrf": csrf_token(request),
        }

    def gate(request: Request):
        """Redirect to the intro or the sign-in when users exist and nobody is signed in."""
        if config.login_required and who(request) is None:
            seen = request.cookies.get("intro") == "1"
            return RedirectResponse("/login" if seen else "/intro", status_code=303)
        return None

    # ---------------------------------------------------------------- entry
    @app.get("/intro", response_class=HTMLResponse)
    def intro(request: Request):
        return templates.TemplateResponse(request, "intro.html", ctx(request))

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, failed: int = 0):
        if who(request):
            return RedirectResponse("/", status_code=303)
        c = ctx(request)
        c["failed"] = bool(failed)
        resp = templates.TemplateResponse(request, "login.html", c)
        resp.set_cookie("intro", "1", samesite="lax", max_age=30 * 24 * 3600)
        return resp

    @app.post("/login")
    async def login(request: Request):
        form = {k: str(v) for k, v in (await request.form()).items()}
        name, password = form.get("name", "").strip(), form.get("password", "")
        if not csrf_ok(request, form):
            return RedirectResponse("/login?failed=1", status_code=303)
        if users.verify(name, password):
            audit.record(name, "cockpit", "session", "login")
            resp = RedirectResponse("/", status_code=303)
            resp.set_cookie("session", users.issue(name), httponly=True, samesite="lax")
            return resp
        audit.record(name or "?", "cockpit", "session", "login", ok=False, reason="bad credentials")
        return RedirectResponse("/login?failed=1", status_code=303)

    @app.get("/logout")
    def logout(request: Request):
        u = who(request)
        if u:
            audit.record(u.name, "cockpit", "session", "logout")
        resp = RedirectResponse("/login", status_code=303)
        resp.delete_cookie("session")
        return resp

    # ---------------------------------------------------------------- pages
    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request):
        if (r := gate(request)):
            return r
        c = ctx(request)
        c["cards"] = build_cards(config, c["_access"], c["role"])
        return templates.TemplateResponse(request, "index.html", c)

    @app.get("/grid", response_class=HTMLResponse)
    def grid(request: Request):
        if (r := gate(request)):
            return r
        c = ctx(request)
        c["cards"] = build_cards(config, c["_access"], c["role"])
        return templates.TemplateResponse(request, "grid.html", c)

    def module_page(request: Request, c: dict, module, outcome=None, ran=None):
        card = card_for(config, c["_access"], c["role"], module.id)
        c["card_"], c["module"] = card, module
        c["raw"] = json.dumps(card.panel, ensure_ascii=False, indent=2) if card and card.panel else ""
        c["outcome"], c["ran"] = outcome, ran
        c["plugin"] = plugins_for(config).get(module.plugin)
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
            return RedirectResponse("/", status_code=303)
        return module_page(request, c, module)

    @app.post("/m/{module_id}/a/{action_id}", response_class=HTMLResponse)
    async def act(request: Request, module_id: str, action_id: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        module = find_module(module_id)
        action = c["_actions"].find(module, action_id) if module else None
        if module is None or action is None:
            return RedirectResponse("/", status_code=303)
        form = {k: str(v) for k, v in (await request.form()).items()}
        try:
            if not csrf_ok(request, form):
                raise Denied("the form token did not match — reload the page and try again")
            outcome = c["_actions"].run(module, action, form, c["role"])
        except Denied as exc:
            outcome = type("O", (), {"ok": False, "output": str(exc), "argv": []})()
        return module_page(request, c, module, outcome, action)

    @app.get("/m/{module_id}/doc/{ref:path}", response_class=HTMLResponse)
    def document(request: Request, module_id: str, ref: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        module = find_module(module_id)
        if module is None or not c["role"].may_open(module_id):
            return RedirectResponse("/", status_code=303)
        try:
            doc = document_for(reader_for(module, config), c["_access"], c["role"], module, config, ref)
        except Denied as exc:
            doc = {"title": ref, "html": f"<p class='hint'>{exc}</p>", "ref": ref}
        if doc is None:
            return RedirectResponse(f"/m/{module_id}", status_code=303)
        c["module"], c["doc"] = module, doc
        return templates.TemplateResponse(request, "document.html", c)

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
            return RedirectResponse("/", status_code=303)
        return setup_page(request, c)

    @app.post("/setup/schema/{schema_id:path}/add", response_class=HTMLResponse)
    async def setup_schema_add(request: Request, schema_id: str):
        if (r := gate(request)):
            return r
        c = ctx(request)
        form = {k: str(v) for k, v in (await request.form()).items()}
        if not c["role"].may_act("setup.schema_add") and not c["role"].may_act("*"):
            return RedirectResponse("/", status_code=303)
        if not csrf_ok(request, form):
            ok, out = False, "the form token did not match — reload the page and try again"
        else:
            ok, out = add_attribute(config, c["_access"], c["role"], schema_id, form)
        return setup_page(request, c, type("O", (), {"ok": ok, "output": out})())

    @app.get("/set")
    def set_prefs(request: Request, lang: str | None = None, role: str | None = None):
        back = request.headers.get("referer", "/")
        resp = RedirectResponse(back, status_code=303)
        if lang and i18n.has(lang):
            resp.set_cookie("lang", lang, samesite="lax", max_age=365 * 24 * 3600)
        if role and config.role_switch and role in config.roles and who(request) is None:
            resp.set_cookie("role", role, samesite="lax")
        return resp

    @app.get("/api/panels")
    def api_panels(request: Request):
        if config.login_required and who(request) is None:
            return JSONResponse({"detail": "sign in first"}, status_code=401)
        c = ctx(request)
        return JSONResponse([{"module": card.module_id, "verdict": card.verdict,
                              "reason": card.reason, "panel": card.panel}
                             for card in build_cards(config, c["_access"], c["role"])])

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
            response.set_cookie("csrf", token, samesite="strict", httponly=False)
        return response

    # Mounted plugin apps sit behind the same gate and the same role check as the pages.
    @app.middleware("http")
    async def guard_apps(request: Request, call_next):
        parts = request.url.path.split("/")
        if len(parts) >= 4 and parts[1] == "m" and parts[3] == "app":
            if config.login_required and who(request) is None:
                return RedirectResponse("/login", status_code=303)
            if not ctx(request)["role"].may_open(parts[2]):
                return RedirectResponse("/", status_code=303)
        return await call_next(request)

    app.state.app_failures = dict(mount_apps(app, config))
    app.state.i18n = i18n
    app.state.users = users
    return app
