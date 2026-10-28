"""Sorting before reading: deterministic rules decide first, the AI only reads what no rule decides, nothing is deleted.

The rules are the rows of the rule matrix (`regeln.json`) that carry a `sort` (beside `match`, which names the case a
delivery is for):

    {"id": "R-09", "kind": "werbung", "action": "file_away", "approval": "auto",
     "sort": {"domains": ["newsletter.example"],            sender domain, subdomains included; the longest rule wins
               "subject": ["herbstaktion"],                   a keyword in the subject (lower case)
               "pattern": "(?P<reference>SN-\\d{4}-\\d{5})",  a regular expression over the subject; named groups become fields
               "bulk": true,                                  mailing-list headers (List-Id, List-Unsubscribe, Precedence)
               "auto": true}}                                 machine-sent (Auto-Submitted), not a list

Order: sender domain, then subject keyword or pattern (in matrix order), then machine-sent, then bulk — the same order the
standalone mail sorter (apps/mailsort) uses for its folders, from where it came. `privacy.never_ai` at the top of
`regeln.json` names sender domains whose mail no AI reads: it waits for a person.

Standard library only, so the mail sorter can use it without the rest of the core.
"""

from __future__ import annotations

import re


def domain_of(address: str) -> str:
    return address.rpartition("@")[2].strip().lower().rstrip(">")


def _domain_match(domain: str, rule: str) -> bool:
    rule = rule.lower()
    return domain == rule or domain.endswith("." + rule)


def classify(h: dict, rules: list[dict]) -> tuple[dict, str, dict] | None:
    """(rule, reason, fields) for the first rule that decides this message, or None — then a helper reads it.
    `h`: domain, subject, list_id, unsubscribe, precedence, auto_submitted."""
    domain, subject = (h.get("domain") or "").lower(), (h.get("subject") or "")
    rows = [r for r in rules if isinstance(r.get("sort"), dict)]
    best = None
    for r in rows:
        for d in r["sort"].get("domains", []):
            if _domain_match(domain, d) and (best is None or len(d) > len(best[1])):
                best = (r, d)
    if best:
        return best[0], f"domain {best[1]}", {}
    low = subject.lower()
    for r in rows:
        for kw in r["sort"].get("subject", []):
            if kw.lower() in low:
                return r, f"subject '{kw}'", {}
        if r["sort"].get("pattern"):
            m = re.search(r["sort"]["pattern"], subject, re.IGNORECASE)
            if m:
                return r, f"subject matches {r['sort']['pattern']}", {k: v for k, v in m.groupdict().items() if v}
    bulk = bool(h.get("list_id") or h.get("unsubscribe") or (h.get("precedence") or "").lower() in ("bulk", "list", "junk"))
    auto = bool(h.get("auto_submitted")) and (h.get("auto_submitted") or "").lower() != "no"
    if auto and not bulk:
        r = next((r for r in rows if r["sort"].get("auto")), None)
        if r:
            return r, f"auto-submitted: {h['auto_submitted']}", {}
    if bulk:
        r = next((r for r in rows if r["sort"].get("bulk")), None)
        if r:
            return r, "list/bulk headers", {}
    return None


def never_ai(h: dict, doc: dict) -> bool:
    """True when the sender's domain is on the privacy list: no AI reads this message."""
    domain = (h.get("domain") or "").lower()
    return any(_domain_match(domain, d) for d in ((doc.get("privacy") or {}).get("never_ai") or []))
