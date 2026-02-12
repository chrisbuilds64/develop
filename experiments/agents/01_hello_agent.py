"""
01_hello_agent.py -- Dein erster Agent

Was ist ein Agent? Im Kern nur DAS HIER:

1. Du schickst eine Nachricht an Claude
2. Claude antwortet -- ODER sagt "ich will ein Tool benutzen"
3. Wenn Tool: Du fuehrst das Tool aus, schickst das Ergebnis zurueck
4. Zurueck zu Schritt 2

Dieser Loop IST der Agent. Alles andere (CrewAI, Agent SDK, OpenClaw)
ist nur Abstraktion drueber.

In diesem Script: Wir bauen den Loop von Hand. Keine Magie.
"""

import anthropic
import json
from pathlib import Path

# --- API Key laden ---
# Liegt in ~/.secrets/chrisbuilds64/ (nicht im Repo!)
API_KEY_PATH = Path.home() / ".secrets" / "chrisbuilds64" / "chrisbuilds64.antrophic.api"
API_KEY = API_KEY_PATH.read_text().strip()

client = anthropic.Anthropic(api_key=API_KEY)

# --- TEIL 1: Einfacher API Call (noch kein Agent!) ---

print("=" * 60)
print("TEIL 1: Einfacher API Call")
print("=" * 60)

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",  # Sonnet = guenstig + schnell fuer Experimente
    max_tokens=256,
    messages=[
        {"role": "user", "content": "What is an AI agent? Answer in exactly 2 sentences."}
    ],
)

print(response.content[0].text)
print()

# Das war KEIN Agent. Das war ein API Call. Einmal fragen, einmal antworten.
# Wie ein Taschenrechner -- du drueckst Enter, kriegst ein Ergebnis.


# --- TEIL 2: Agent mit Tool Loop ---

print("=" * 60)
print("TEIL 2: Agent mit Tool -- DER LOOP")
print("=" * 60)

# Wir definieren ein Tool. Ein Tool ist einfach eine Funktion
# die der Agent AUFRUFEN DARF, wenn er will.

# Tool-Definition (JSON Schema -- das liest Claude um zu entscheiden ob/wann er es nutzt)
tools = [
    {
        "name": "get_current_time",
        "description": "Returns the current date and time. Use this when you need to know what time it is.",
        "input_schema": {
            "type": "object",
            "properties": {},  # Keine Parameter noetig
            "required": [],
        },
    }
]


# Tool-Implementation (die echte Python-Funktion)
def get_current_time() -> str:
    from datetime import datetime
    now = datetime.now()
    return now.strftime("%A, %d %B %Y, %H:%M:%S")


# DER AGENT LOOP
# Das ist der Kern. Alles was ein Agent tut, passiert hier.

messages = [
    {"role": "user", "content": "What time is it right now? And what day of the week?"}
]

print(f"\nUser: {messages[0]['content']}\n")

# Loop laeuft so lange bis Claude KEIN Tool mehr aufrufen will
while True:
    # Schritt 1: Claude fragen
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )

    # Schritt 2: Was hat Claude geantwortet?
    # stop_reason == "tool_use" -> Claude will ein Tool benutzen
    # stop_reason == "end_turn" -> Claude ist fertig

    if response.stop_reason == "end_turn":
        # Fertig! Letzte Antwort ausgeben
        for block in response.content:
            if hasattr(block, "text"):
                print(f"Agent: {block.text}")
        break

    # Schritt 3: Claude will ein Tool benutzen
    # response.content enthaelt BEIDES: Text UND Tool Calls
    tool_results = []

    for block in response.content:
        if block.type == "text":
            print(f"Agent (denkt): {block.text}")

        elif block.type == "tool_use":
            tool_name = block.name
            tool_input = block.input
            tool_id = block.id

            print(f"Agent -> Tool Call: {tool_name}({json.dumps(tool_input)})")

            # Tool ausfuehren
            if tool_name == "get_current_time":
                result = get_current_time()
            else:
                result = f"Unknown tool: {tool_name}"

            print(f"Tool Result: {result}")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                }
            )

    # Schritt 4: Ergebnis zurueck an Claude
    # Claude's Antwort kommt in die Message History
    messages.append({"role": "assistant", "content": response.content})
    # Tool Results als User-Nachricht (so funktioniert die API)
    messages.append({"role": "user", "content": tool_results})

    # Zurueck zu Schritt 1 -- Loop wiederholt sich


# --- ZUSAMMENFASSUNG ---

print()
print("=" * 60)
print("WAS GERADE PASSIERT IST:")
print("=" * 60)
print()
print("1. Wir haben Claude eine Frage gestellt")
print("2. Claude hat entschieden: 'Ich brauche das Tool get_current_time'")
print("3. Wir haben das Tool ausgefuehrt und das Ergebnis zurueckgeschickt")
print("4. Claude hat das Ergebnis genommen und die finale Antwort formuliert")
print()
print("DAS ist ein Agent. Ein LLM das selbst entscheidet welche")
print("Tools es wann benutzt, und iterativ arbeitet bis die Aufgabe erledigt ist.")
print()
print(f"API Calls in diesem Loop: {len(messages) // 2 + 1}")
print(f"Tool Calls: {sum(1 for m in messages if isinstance(m.get('content', ''), list))}")
