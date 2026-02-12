"""
02_content_analyst.py -- Agent mit System Prompt

Neu gegenueber 01: System Prompt.

Der System Prompt ist das Aequivalent zu OpenClaw's SOUL.md / AGENTS.md.
Er definiert WER der Agent ist, WAS er kann, und NACH WELCHEN REGELN er arbeitet.

Das ist die "Backstory" aus dem CrewAI-Handover -- nur ohne Framework.
"""

import anthropic
import json
from pathlib import Path

# --- Setup ---
API_KEY_PATH = Path.home() / ".secrets" / "chrisbuilds64" / "chrisbuilds64.antrophic.api"
API_KEY = API_KEY_PATH.read_text().strip()
client = anthropic.Anthropic(api_key=API_KEY)

# --- DER SYSTEM PROMPT ---
# Das ist das Herzstuck. Hier steckt das ganze "Prompt Engineering".
# Je praeziser die Regeln, desto besser das Ergebnis.

SYSTEM_PROMPT = """You are a Content QA Analyst for the brand "ChrisBuilds64".

Your job: Review content packages before they get published.

## Who You Work For
Christian Moser, 61, IT consultant turned AI strategist. Building in public.
He publishes on Substack (newsletter) and LinkedIn (posts + articles).

## Content Hierarchy (CRITICAL -- this is the publishing order)
1. **Substack** = MASTER CONTENT (detailed, logbook format, written FIRST)
2. **LinkedIn Post** = Independent narrative (same core, different form, NOT a compressed Substack)
3. **LinkedIn Article** = Substack adapted for LinkedIn (published 2-5 days after Post)
4. **TikTok/Instagram** = Attention only, reference back to Substack

Rule: Substack = Source. Everything else = Derivative. Never reversed.

## Substack Format Rules
- Must start with LOGBOOK ENTRY header (Date, Location, Time, Weather, Mood, Track)
- Section headers must be ALL CAPS (## THE SETUP, ## THE PUNCHLINE)
- Must end with sign-off: --Chris
- Outro: Day number, bio, subscribe link

## LinkedIn Post Rules
- Must be an INDEPENDENT narrative (not just shortened Substack)
- Must have a strong hook (first 2 lines)
- No link in the post body (link goes in First Comment)
- Never sound like a teaser ("want more? Go to Substack")
- Max 3000 characters

## First Comment Rules
- Must be a Curiosity or Identification hook
- NEVER just "Full article here" or "Link to Substack"

## Review Criteria
For each piece of content, evaluate:
1. **Format compliance** (does it follow the rules above?)
2. **Hook quality** (1-10, with justification)
3. **Standalone value** (would this be valuable even without the other pieces?)
4. **Cross-piece consistency** (do all pieces tell the same core story?)
5. **Specific improvements** (2-3 actionable suggestions)

Be direct. Be critical. No fluff. Christian respects honest feedback.
"""

# --- Test Content (hardcoded fuer jetzt) ---

TEST_POST = """I've been writing code for 40 years.

And I keep seeing the same 5 bugs.

Not in the code.
In the people writing it.

1. The "I'll document it later" bug
(Later never comes. You know this.)

2. The "just one more feature" bug
(Scope creep kills projects. Not complexity.)

3. The "works on my machine" bug
(If it only works on YOUR machine, it doesn't work.)

4. The "premature optimization" bug
(You're solving performance problems you don't have yet.)

5. The "we'll refactor later" bug
(Later = never. See bug #1.)

40 years.
Same patterns.
Different languages, same humans.

The bugs aren't in your code.
They're in your habits.

--

Which of these bugs do you recognize in yourself?

#SoftwareEngineering #BuildingInPublic #ChrisBuilds64"""

# --- Agent Loop (gleiche Struktur wie 01, aber mit System Prompt) ---

messages = [
    {
        "role": "user",
        "content": f"Review this LinkedIn post:\n\n{TEST_POST}",
    }
]

print("Content QA Analyst reviewing LinkedIn Post...")
print("=" * 60)

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2048,
    system=SYSTEM_PROMPT,  # <-- DAS ist neu. Der System Prompt.
    messages=messages,
)

# Kein Tool Loop noetig -- der Analyst braucht hier nur "denken"
# (Agent ohne Tools = Berater der nur reden kann, wie im Handover beschrieben)

for block in response.content:
    if hasattr(block, "text"):
        print(block.text)

print()
print("=" * 60)
print("WAS NEU WAR:")
print("=" * 60)
print()
print("1. System Prompt = Wer ist der Agent, was sind seine Regeln")
print("2. Ohne Tools: Agent kann nur analysieren/schreiben (Berater)")
print("3. Der System Prompt ist das Aequivalent zu OpenClaw's SOUL.md")
print("4. Qualitaet des Outputs haengt DIREKT von der Qualitaet des System Prompts ab")
