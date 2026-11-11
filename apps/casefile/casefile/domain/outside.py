"""Work for a case that runs outside it (REQ-001 T-08): a deploy through a request service, a job somewhere else.

Whoever hands the work out records it in the case (`outside` step): what, in a key the application's vocabulary words
(`outside.<what>`), since when and by whom, in `meta.json` under `outside`. It ends with the report that comes back —
the next order on the case (a report arrives as an order for a helper) — or with an explicit `outside_end`. While it
stands, the case's move is "wait", like a helper at work, and nobody holds it. The core names no kind of work.
"""

from __future__ import annotations

import datetime as dt
import re

from ..config import DomainConfig
from ..models import Case

KEY = "outside"
WHAT = re.compile(r"^[a-z][a-z0-9_-]{0,60}$")


def _at(stamp: str | None) -> dt.datetime | None:
    try:
        t = dt.datetime.fromisoformat(str(stamp))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.astimezone()


def standing(case: Case) -> dict | None:
    """The outside work the case carries, while no order came after it; else None."""
    doc = case.meta.get(KEY)
    if not isinstance(doc, dict) or not doc.get("what"):
        return None
    since = _at(doc.get("since"))
    if since is None:
        return None
    if any((t := _at(r.created)) is not None and t > since for r in case.runs):
        return None                                           # the report came back as an order
    return doc


def words(config: DomainConfig, doc: dict, lang: str | None) -> str:
    """'Deploy auf ENTW läuft': the work in the vocabulary's words, in the sentence `texts.outside_running`."""
    what = config.word("outside", str(doc["what"]), lang, str(doc["what"]))
    core = "{what} läuft" if (lang or config.lang) == "de" else "{what} running"
    return config.word("texts", "outside_running", lang, core).replace("{what}", what)
