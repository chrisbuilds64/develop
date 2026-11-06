"""The AI team in the public demo: the visitor's helpers, their sessions and the folder the logs go to (ADR-020).

Helpers belong to the person, not to a workspace. Inside the cockpit the team is the person's real one, and the
surface talks to the cockpit for it (`/api/cf-team` there). In the public demo there is no cockpit, so the visitor
keeps a small team of their own here: one file, `team.json`, in a folder beside the sandboxes, shared by every
world they open. Answers are prepared, like the rest of the demo: no model is called.
"""

from __future__ import annotations

import datetime as dt
import json
import secrets
import threading
from pathlib import Path

# Job profiles: id → (label, what it does, what it never does), English and German.
PROFILES: dict[str, dict[str, tuple[str, str, str]]] = {
    "mail": {"en": ("Mail reader", "Reads incoming mail, sorts it and proposes a next step.", "It only reads and proposes. You confirm every step."),
             "de": ("Postleser", "Liest eingehende Mails, sortiert sie und schlägt den nächsten Schritt vor.", "Er liest und schlägt nur vor. Jeden Schritt bestätigst du.")},
    "quote": {"en": ("Quote calculator", "Prices a quote request from the facts in the file.", "It uses the tariff and the facts in the file, and shows how it got to the price."),
              "de": ("Angebotsrechner", "Berechnet eine Anfrage aus den Fakten in der Akte.", "Er nutzt den Tarif und die Fakten der Akte und zeigt, wie er auf den Preis kommt.")},
    "check": {"en": ("Assessment checker", "Compares an assessment with the claim and flags gaps.", "It also spots contradictions between documents. The decision stays with you."),
              "de": ("Gutachtenprüfer", "Vergleicht ein Gutachten mit dem Schaden und markiert Lücken.", "Er findet auch Widersprüche zwischen Dokumenten. Die Entscheidung bleibt bei dir.")},
    "letter": {"en": ("Letter writer", "Drafts customer letters from approved templates.", "It only uses approved templates, so every letter stays correct."),
               "de": ("Briefschreiber", "Entwirft Kundenbriefe aus freigegebenen Vorlagen.", "Er nutzt nur freigegebene Vorlagen, damit jeder Brief stimmt.")},
    "pattern": {"en": ("Pattern spotter", "Finds duplicates and repeats across cases.", "It never decides. It shows what looks alike and why, and you judge."),
                "de": ("Musterfinder", "Findet Doppelungen und Wiederholungen über Fälle hinweg.", "Er entscheidet nie. Er zeigt, was sich ähnelt und warum, und du urteilst.")},
}
MODELS = {"standard": {"en": "Standard", "de": "Standard"}, "fast": {"en": "Fast", "de": "Schnell"}, "thorough": {"en": "Thorough", "de": "Gründlich"}}

SUGGEST = {
    "mail": {"en": ["What came in today?", "Which mails need me first?", "Summarise the burst pipe mail"],
             "de": ["Was ist heute reingekommen?", "Welche Mails brauchen mich zuerst?", "Fass die Mail zum Rohrbruch zusammen"]},
    "quote": {"en": ["Which quotes wait for approval?", "How was the Tiguan price made?"],
              "de": ["Welche Angebote warten auf Freigabe?", "Wie kam der Preis für den Tiguan zustande?"]},
    "check": {"en": ["Check the A3 assessment for gaps", "What is still missing?"],
              "de": ["Prüf das Gutachten zur A3 auf Lücken", "Was fehlt noch?"]},
    "letter": {"en": ["Draft a reply to Erika Brandt", "Write the cover letter for the Mazda quote"],
               "de": ["Entwirf eine Antwort an Erika Brandt", "Schreib das Anschreiben zum Mazda-Angebot"]},
    "pattern": {"en": ["Any duplicate claims this week?", "Which claims look alike?"],
                "de": ["Gibt es diese Woche doppelte Schäden?", "Welche Schäden ähneln sich?"]},
}

# The first answer of a session, from what the sample worlds hold; every later one is a plain acknowledgement.
FIRST = {
    "mail": {"en": "I am reading a new mail about a burst pipe in a flat. The others are sorted and wait for your decision in the Inbox. Should I go through them with you?",
             "de": "Ich lese gerade eine neue Mail zu einem Rohrbruch in einer Wohnung. Die anderen sind sortiert und warten im Posteingang auf deine Entscheidung. Soll ich sie mit dir durchgehen?"},
    "quote": {"en": "The Tiguan quote comes to 1,322.57 € a year. It is higher than usual because the youngest driver is 19. Should I show you the calculation?",
              "de": "Das Angebot für den Tiguan liegt bei 1.322,57 € im Jahr. Es ist höher als üblich, weil der jüngste Fahrer 19 ist. Soll ich dir die Rechnung zeigen?"},
    "check": {"en": "The assessment for the rear-end collision on the A3 is in: repair 2,900 €. Should I compare it with the claim?",
              "de": "Das Gutachten zum Auffahrunfall auf der A3 liegt vor: Reparatur 2.900 €. Soll ich es mit dem Schaden vergleichen?"},
    "letter": {"en": "Here is a first draft, built only from approved templates. Read it and tell me what to change.",
               "de": "Hier ist ein erster Entwurf, nur aus freigegebenen Vorlagen. Lies ihn und sag mir, was ich ändern soll."},
    "pattern": {"en": "Two claims come from the same address, Musterstraße 12: water damage and a burglary. Different kinds of damage, but worth a look.",
                "de": "Zwei Schäden kommen von derselben Adresse, Musterstraße 12: ein Wasserschaden und ein Einbruch. Verschiedene Schadenarten, aber einen Blick wert."},
}
NOTED = {"en": "Noted. I have added that to this session’s log.", "de": "Notiert. Ich habe es ins Protokoll dieser Sitzung aufgenommen."}
NEW = {"en": "New session", "de": "Neue Sitzung"}


def _t(v, lang: str) -> str:
    return v if isinstance(v, str) else (v.get(lang) or v.get("en") or "")


def _now() -> str:
    return dt.datetime.now().strftime("%H:%M")


def seed() -> dict:
    return {"team": [{"id": "mail", "model": "standard"}, {"id": "quote", "model": "standard"}, {"id": "check", "model": "thorough"}],
            "sessions": [
                {"id": "s3", "agent": "quote", "start": "09:38", "end": "09:41",
                 "topic": {"en": "Mazda 2, liability only", "de": "Mazda 2, nur Haftpflicht"}, "note": {"en": "Quote priced", "de": "Angebot berechnet"},
                 "turns": [{"who": "you", "text": {"en": "Please price the Mazda 2, liability only.", "de": "Bitte rechne den Mazda 2, nur Haftpflicht."}},
                           {"who": "ai", "text": {"en": "Done: 412.60 € a year. The quote is in the file.", "de": "Fertig: 412,60 € im Jahr. Das Angebot liegt in der Akte."}}]},
                {"id": "s2", "agent": "check", "start": "09:05", "end": "09:12",
                 "topic": {"en": "Fall on black ice", "de": "Sturz auf Glatteis"}, "note": {"en": "Settlement checked", "de": "Regulierung geprüft"},
                 "turns": [{"who": "you", "text": {"en": "Check the settlement for the fall on black ice.", "de": "Prüf die Regulierung zum Sturz auf Glatteis."}},
                           {"who": "ai", "text": {"en": "Liability is confirmed and the documents agree with each other. Nothing is missing.", "de": "Die Haftung ist bestätigt und die Unterlagen passen zusammen. Es fehlt nichts."}}]},
                {"id": "s1", "agent": "mail", "start": "08:54", "end": "08:55",
                 "topic": {"en": "Inbox", "de": "Posteingang"}, "note": {"en": "Two mails sorted", "de": "Zwei Mails sortiert"},
                 "turns": [{"who": "ai", "text": {"en": "Read two new mails: a claim report and a newsletter. Proposals are ready.", "de": "Zwei neue Mails gelesen: eine Schadenmeldung und ein Newsletter. Vorschläge liegen bereit."}}]},
            ], "n": 4, "logs": "/sandbox/sessions/logs"}


class TeamError(Exception):
    """A sentence for the person."""


class DemoTeam:
    """One visitor's team in one file. Small, so every change rewrites it."""

    _lock = threading.Lock()

    def __init__(self, folder: Path):
        self.dir = folder
        self.file = folder / "team.json"

    @classmethod
    def create(cls, base: Path) -> "DemoTeam":
        d = base / f"team-{secrets.token_urlsafe(9)}"
        d.mkdir(parents=True)
        (d / ".created").write_text(dt.datetime.now().isoformat(), encoding="utf-8")
        t = cls(d)
        t._save(seed())
        return t

    def _load(self) -> dict:
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return seed()

    def _save(self, data: dict) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.file)

    # ---------------------------------------------------------------- views
    def view(self, lang: str) -> dict:
        d = self._load()
        open_ = {s["agent"]: s["id"] for s in d["sessions"] if not s.get("end")}
        on = {a["id"] for a in d["team"]}
        return {
            "source": "demo",
            "agents": [{"id": a["id"], "label": PROFILES[a["id"]][lang][0], "role": PROFILES[a["id"]][lang][1], "model": a.get("model"),
                        "session": open_.get(a["id"])} for a in d["team"] if a["id"] in PROFILES],
            "hireable": [{"id": k, "label": v[lang][0], "role": v[lang][1], "taken": k in on} for k, v in PROFILES.items()],
            "models": [{"id": k, "label": v[lang]} for k, v in MODELS.items()],
            "sessions": [self._head(s, lang) for s in d["sessions"] if s.get("end")],
            "logs_dir": d.get("logs", ""),
        }

    def _head(self, s: dict, lang: str) -> dict:
        p = PROFILES.get(s["agent"], {}).get(lang, (s["agent"], "", ""))
        return {"id": s["id"], "agent": s["agent"], "label": p[0], "topic": _t(s.get("topic", ""), lang),
                "note": _t(s.get("note", ""), lang), "started": s.get("start"), "ended": s.get("end")}

    def session(self, sid: str, lang: str) -> dict:
        s = self._find(self._load(), sid)
        p = PROFILES.get(s["agent"], {}).get(lang, (s["agent"], "", ""))
        topic = _t(s.get("topic", ""), lang)
        return {**self._head(s, lang), "topic": "" if topic == NEW[lang] or not topic else topic, "role": p[1], "does": p[2],
                "status": "closed" if s.get("end") else "open",
                "turns": [{"who": t["who"], "text": _t(t["text"], lang)} for t in s.get("turns", [])],
                "suggestions": SUGGEST.get(s["agent"], {}).get(lang, []) if not s.get("turns") and not s.get("end") else []}

    @staticmethod
    def _find(d: dict, sid: str) -> dict:
        for s in d["sessions"]:
            if s["id"] == sid:
                return s
        raise TeamError("There is no such session.")

    # ---------------------------------------------------------------- changes
    def hire(self, profile: str, model: str) -> None:
        with self._lock:
            d = self._load()
            if profile not in PROFILES:
                raise TeamError("There is no such job profile.")
            if any(a["id"] == profile for a in d["team"]):
                raise TeamError("This helper is already on the team.")
            d["team"].append({"id": profile, "model": model if model in MODELS else "standard"})
            self._save(d)

    def dismiss(self, agent: str) -> None:
        with self._lock:
            d = self._load()
            d["team"] = [a for a in d["team"] if a["id"] != agent]
            for s in d["sessions"]:
                if s["agent"] == agent and not s.get("end"):
                    s["end"] = _now()
                    s["note"] = {"en": "Ended when the helper was removed", "de": "Beendet, als der Helfer entfernt wurde"}
            self._save(d)

    def set_logs(self, folder: str) -> None:
        with self._lock:
            d = self._load()
            d["logs"] = folder.strip()[:300]
            self._save(d)

    def start(self, agent: str) -> str:
        with self._lock:
            d = self._load()
            if not any(a["id"] == agent for a in d["team"]):
                raise TeamError("This helper is not on your team.")
            for s in d["sessions"]:
                if s["agent"] == agent and not s.get("end"):
                    return s["id"]
            sid = f"s{d['n']}"
            d["n"] += 1
            d["sessions"].insert(0, {"id": sid, "agent": agent, "start": _now(), "end": None, "topic": dict(NEW), "note": "", "turns": []})
            self._save(d)
            return sid

    def say(self, sid: str, text: str) -> None:
        text = text.strip()[:4000]
        if not text:
            raise TeamError("Write something first.")
        with self._lock:
            d = self._load()
            s = self._find(d, sid)
            if s.get("end"):
                raise TeamError("This session has ended.")
            first = not any(t["who"] == "ai" for t in s["turns"])
            s["turns"].append({"who": "you", "text": text})
            if isinstance(s.get("topic"), dict) and s["topic"].get("en") == NEW["en"]:
                s["topic"] = text[:48] + ("…" if len(text) > 48 else "")
            s["turns"].append({"who": "ai", "text": dict(FIRST.get(s["agent"], NOTED)) if first else dict(NOTED)})
            self._save(d)

    def end(self, sid: str, note: str) -> None:
        note = note.strip()[:500]
        if not note:
            raise TeamError("Please add a closing note.")
        with self._lock:
            d = self._load()
            s = self._find(d, sid)
            if not s.get("end"):
                s["end"] = _now()
                s["note"] = note
                if isinstance(s.get("topic"), dict) and s["topic"].get("en") == NEW["en"]:
                    s["topic"] = ""
            self._save(d)
