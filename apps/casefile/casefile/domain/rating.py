"""Rating: a quote computed from a questionnaire and a rate table — by the core, never by the AI.

The helper fills the questionnaire (`fragebogen.json`) from what the customer wrote; this module turns the answers into
a premium. Every line shows its base and each factor with the answer it came from, so the number can be followed by
hand. A missing answer is a refusal that names it — the quote is never guessed.

The table is configuration (`tarif.json`, the pipeline root's copy wins over the domain's):

    {"name": "…", "tax": {"word": "…", "rate": 0.19},
     "products": {"KFZ": {"word": "…", "coverages": [
         {"id": "kh", "word": "…", "base": 420, "factors": ["sf", "km"]},
         {"id": "vk", "word": "…", "base": 520, "when": {"kasko": "vollkasko"}, "factors": ["sf"]},
         {"id": "hr", "word": "…", "per": {"field": "wohnflaeche", "rate": 1.6, "unit": "m²"}, "factors": []}]}},
     "factors": {"sf": {"field": "sf_klasse", "word": "…", "bands": [[0, 0, 1.3], [1, 4, 1.0]]},
                 "garage": {"field": "garage", "word": "…", "table": {"ja": 0.9, "nein": 1.0}}}}

The questionnaire: `{"product": "KFZ", "fields": [{"id": "sf_klasse", "word": "…", "value": 12, "quote": "…"}, …]}`.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal

from ..config import DomainConfig
from ..store import FsStore


class RatingError(Exception):
    """A sentence for the person."""


def table(store: FsStore, config: DomainConfig) -> dict:
    for p in (store.root / "tarif.json", (config.dir / "tarif.json") if config.dir else None):
        if p and p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    raise RatingError("no rate table (tarif.json) in this application")


def _money(x: float) -> float:
    """Cents, rounded commercially (half up) — binary floats would round 83.695 down."""
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _answers(form: dict) -> tuple[dict, dict]:
    values, words = {}, {}
    for f in form.get("fields") or []:
        if isinstance(f, dict) and f.get("id"):
            words[f["id"]] = f.get("word") or f["id"]
            if f.get("value") not in (None, "") and not f.get("missing"):
                values[f["id"]] = f["value"]
    return values, words


def _applies(when: dict, values: dict) -> bool:
    for field, want in (when or {}).items():
        have = str(values.get(field, "")).strip().lower()
        if have not in [str(w).lower() for w in (want if isinstance(want, list) else [want])]:
            return False
    return True


def _factor(spec: dict, value) -> float:
    if "table" in spec:
        key = str(value).strip().lower()
        for k, f in spec["table"].items():
            if k.lower() == key:
                return float(f)
        raise RatingError(f"{spec.get('word', spec['field'])}: „{value}“ is not in the rate table")
    try:
        n = float(str(value).replace(".", "").replace(",", ".")) if isinstance(value, str) else float(value)
    except ValueError:
        raise RatingError(f"{spec.get('word', spec['field'])}: „{value}“ is not a number") from None
    for lo, hi, f in spec.get("bands") or []:
        if lo <= n <= hi:
            return float(f)
    raise RatingError(f"{spec.get('word', spec['field'])}: {value} lies outside the rate table")


def rate(form: dict, tariff: dict) -> dict:
    """The quote as data. Raises RatingError naming every answer that is missing."""
    product = tariff.get("products", {}).get(form.get("product", ""))
    if not product:
        raise RatingError(f"the rate table has no product „{form.get('product', '')}“")
    values, words = _answers(form)
    factors = tariff.get("factors", {})
    covers = [c for c in product.get("coverages", []) if all(k in values for k in (c.get("when") or {})) and _applies(c.get("when"), values)]
    needed = {k for c in product.get("coverages", []) for k in (c.get("when") or {})}
    needed |= {factors[f]["field"] for c in covers for f in c.get("factors", []) if f in factors}
    needed |= {c["per"]["field"] for c in covers if c.get("per")}
    missing = [words.get(k, k) for k in sorted(needed) if k not in values]
    if missing:
        raise RatingError((tariff.get("words") or {}).get("missing", "still missing for the quote: {fields}").format(fields=", ".join(missing)))
    lines, net = [], 0.0
    for c in covers:
        if c.get("per"):
            amount = float(values[c["per"]["field"]]) * float(c["per"]["rate"])
            base = {"word": f"{values[c['per']['field']]} {c['per'].get('unit', '')} × {c['per']['rate']:.2f} €".replace(".", ","), "amount": _money(amount)}
        else:
            amount = float(c["base"])
            base = {"word": "", "amount": amount}
        used = []
        for fid in c.get("factors", []):
            spec = factors[fid]
            f = _factor(spec, values[spec["field"]])
            used.append({"word": spec.get("word", spec["field"]), "answer": values[spec["field"]], "factor": f})
            amount *= f
        amount = _money(amount)
        net += amount
        lines.append({"id": c["id"], "word": c.get("word", c["id"]), "base": base, "factors": used, "amount": amount})
    net = _money(net)
    tax = tariff.get("tax") or {}
    tax_amount = _money(net * float(tax.get("rate", 0)))
    gross = _money(net + tax_amount)
    return {"product": form["product"], "product_word": product.get("word", form["product"]), "tariff": tariff.get("name", ""),
            "lines": lines, "net": net, "tax": {"word": tax.get("word", "Tax"), "rate": tax.get("rate", 0), "amount": tax_amount},
            "gross": gross, "monthly": _money(gross / 12)}


def _eur(x: float) -> str:
    return f"{x:,.2f} €".replace(",", "x").replace(".", ",").replace("x", ".")


WORDS = {"title": "Quote", "base": "Base premium", "premium": "Premium", "net": "Net premium", "year": "Annual premium",
         "monthly": "monthly", "by": "computed by the rate table, not by the AI"}


def render(quote: dict, words: dict | None = None) -> str:
    """The quote as a document a person can check line by line. The words come from the rate table's `words`."""
    w = {**WORDS, **(words or {})}
    out = [f"# {w['title']} · {quote['product_word']}", "", f"*{quote['tariff']} · {w['by']}*", ""]
    for line in quote["lines"]:
        out += [f"## {line['word']}", "", "| | | |", "|---|---|---:|", f"| {line['base']['word'] or w['base']} | | {_eur(line['base']['amount'])} |"]
        out += [f"| {f['word']} | {f['answer']} | × {str(f['factor']).replace('.', ',')} |" for f in line["factors"]]
        out += [f"| **{w['premium']}** | | **{_eur(line['amount'])}** |", ""]
    t = quote["tax"]
    out += [f"## {w['year']}", "", "| | |", "|---|---:|", f"| {w['net']} | {_eur(quote['net'])} |",
            f"| {t['word']} {round(float(t['rate']) * 100)} % | {_eur(t['amount'])} |", f"| **{w['year']}** | **{_eur(quote['gross'])}** |",
            f"| {w['monthly']} | {_eur(quote['monthly'])} |", ""]
    return "\n".join(out)


def compile_quote(store: FsStore, config: DomainConfig, case_id: str) -> dict:
    """Rate the case's newest questionnaire and leave `angebot.json` and `angebot.md` beside it. Raises RatingError, writes nothing then."""
    from .cases import split_version
    stage = store.find(case_id)
    versions = sorted((split_version(f)[1], f) for f in store.files(case_id) if split_version(f)[0] == "fragebogen.json")
    if not versions:
        raise RatingError("the questionnaire (fragebogen.json) is missing")
    rel = f"{stage}/{case_id}/{versions[-1][1]}"                   # the newest version: an answer added later is a v2
    tariff = table(store, config)
    quote = rate(store.read_json(rel), tariff)
    store.write_json(f"{stage}/{case_id}/angebot.json", quote)
    store.write_atomic(f"{stage}/{case_id}/angebot.md", render(quote, tariff.get("words")))
    return {"gross": quote["gross"], "lines": len(quote["lines"])}
