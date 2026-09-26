"""One self-contained HTML file: the overview, CSS inlined, no server needed.

For the email attachment, the projector, the leave-behind. Same templates,
same cards, same language — only the controls and the refresh are gone,
because there is nothing to talk to.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import __version__
from .access import Access
from .audit import AuditLog
from .config import Config
from .i18n import I18n
from .registry import build_cards

HERE = Path(__file__).parent


def render(config: Config, lang: str | None = None, role_id: str | None = None, user: str | None = None) -> str:
    from .registry import plugins_for
    from .users import Users
    i18n = I18n(HERE / "locales")
    for plugin in plugins_for(config).values():
        if plugin.locales and plugin.locales.is_dir():
            i18n.merge(plugin.locales)
    lang = i18n.pick(lang, config.locale)
    variables, role = {}, config.role(role_id)
    if user:
        u = Users(config.users_path, config.secret_path).get(user, config.base_dir)
        if u is None:
            raise SystemExit(f"no such user: {user}")
        variables, role = u.as_vars(), config.roles.get(u.role, role)
    access = Access(config, AuditLog(config.audit_path), variables)
    cards = build_cards(config, access, role)

    env = Environment(loader=FileSystemLoader(HERE / "templates"),
                      autoescape=select_autoescape(["html"]))
    tpl = env.get_template("index.html")
    return tpl.render(
        config=config, lang=lang, languages=i18n.languages(), role=role, roles=[],
        t=lambda key, **kw: i18n.t(lang, key, **kw), version=__version__,
        export=True, user=None, inline_css=(HERE / "static" / "cockpit.css").read_text(encoding="utf-8"),
        cards=cards, modules_by_id={m.id: m for m in config.modules},
        now=dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
    )


def write(config: Config, out: Path, lang: str | None = None, role_id: str | None = None, user: str | None = None) -> Path:
    out = Path(out)
    out.write_text(render(config, lang, role_id, user), encoding="utf-8")
    return out
