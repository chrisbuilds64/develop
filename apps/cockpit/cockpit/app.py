"""The surface: an overview of cards, one page per module, a language switch.

Server-rendered. No build step. The only JavaScript is htmx, shipped as a
file, used for nothing more than refreshing the grid in place.

Language and role live in cookies. The role cookie is honoured only when the
configuration allows switching — there is no sign-in, so a switch is a way to
pick any role, and that must be a deliberate choice on a private machine.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .access import Access, Denied
from .actions import Actions
from .audit import AuditLog
from .config import Config
from .i18n import I18n
from .panel import SCHEMA_PATH
from .registry import build_cards, card_for

HERE = Path(__file__).parent


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title=config.name, version=__version__, docs_url="/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")

    i18n = I18n(HERE / "locales")
    audit = AuditLog(config.audit_path)
    access = Access(config, audit)
    actions = Actions(config, access, audit)

    def ctx(request: Request) -> dict:
        lang = i18n.pick(request.cookies.get("lang"), config.locale)
        role_id = request.cookies.get("role") if config.role_switch else None
        role = config.role(role_id if role_id in config.roles else None)
        return {
            "request": request,
            "config": config,
            "lang": lang,
            "languages": i18n.languages(),
            "role": role,
            "roles": list(config.roles) if config.role_switch else [],
            "t": lambda key, **kw: i18n.t(lang, key, **kw),
            "version": __version__,
            "export": False,
            "modules_by_id": {m.id: m for m in config.modules},
            "now": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
        }

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request):
        c = ctx(request)
        c["cards"] = build_cards(config, access, c["role"])
        return templates.TemplateResponse(request, "index.html", c)

    @app.get("/grid", response_class=HTMLResponse)
    def grid(request: Request):
        """The card grid alone — what htmx swaps in on refresh."""
        c = ctx(request)
        c["cards"] = build_cards(config, access, c["role"])
        return templates.TemplateResponse(request, "grid.html", c)

    @app.get("/m/{module_id}", response_class=HTMLResponse)
    def module(request: Request, module_id: str):
        c = ctx(request)
        card = card_for(config, access, c["role"], module_id)
        if card is None:
            return RedirectResponse("/", status_code=303)
        c["card_"] = card   # `card` is the template macro's name
        c["module"] = next(m for m in config.modules if m.id == module_id)
        c["raw"] = json.dumps(card.panel, ensure_ascii=False, indent=2) if card.panel else ""
        c["outcome"] = None
        return templates.TemplateResponse(request, "module.html", c)

    @app.post("/m/{module_id}/a/{action_id}", response_class=HTMLResponse)
    async def act(request: Request, module_id: str, action_id: str):
        """Run a declared action through the tool's own command; show what it said."""
        c = ctx(request)
        module = next((m for m in config.modules if m.id == module_id), None)
        action = actions.find(module, action_id) if module else None
        if module is None or action is None:
            return RedirectResponse("/", status_code=303)
        form = {k: str(v) for k, v in (await request.form()).items()}
        try:
            outcome = actions.run(module, action, form, c["role"])
        except Denied as exc:
            outcome = type("O", (), {"ok": False, "output": str(exc), "argv": []})()
        c["card_"] = card_for(config, access, c["role"], module_id)
        c["module"] = module
        c["raw"] = json.dumps(c["card_"].panel, ensure_ascii=False, indent=2) if c["card_"] and c["card_"].panel else ""
        c["outcome"] = outcome
        c["ran"] = action
        return templates.TemplateResponse(request, "module.html", c)

    @app.get("/set")
    def set_prefs(request: Request, lang: str | None = None, role: str | None = None):
        back = request.headers.get("referer", "/")
        resp = RedirectResponse(back, status_code=303)
        if lang and i18n.has(lang):
            resp.set_cookie("lang", lang, samesite="lax")
        if role and config.role_switch and role in config.roles:
            resp.set_cookie("role", role, samesite="lax")
        return resp

    @app.get("/api/panels")
    def api_panels(request: Request):
        """Every card as JSON — the same data the page shows, for tools and agents."""
        c = ctx(request)
        return JSONResponse([{
            "module": card.module_id, "verdict": card.verdict,
            "reason": card.reason, "panel": card.panel,
        } for card in build_cards(config, access, c["role"])])

    # The contract, once, in the same document that describes the routes.
    # OpenAPI 3.1 speaks JSON Schema 2020-12, so the file goes in unchanged.
    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        schema.setdefault("components", {}).setdefault("schemas", {})["Panel"] = \
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        app.openapi_schema = schema
        return schema
    app.openapi = openapi

    app.state.access = access
    app.state.i18n = i18n
    app.state.templates = templates
    return app
