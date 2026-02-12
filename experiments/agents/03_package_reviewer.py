"""
03_package_reviewer.py -- Agent mit Custom Tools

Neu gegenueber 02: Der Agent hat TOOLS.

Er kann jetzt:
- Dateien aus einem DAY-Paket auflisten
- Einzelne Dateien lesen
- Content-Regeln laden

ER entscheidet was er liest und in welcher Reihenfolge.
Das ist der Unterschied zwischen Berater (02) und Handwerker (03).
"""

import anthropic
import json
import glob
from pathlib import Path

# --- Setup ---
API_KEY_PATH = Path.home() / ".secrets" / "chrisbuilds64" / "chrisbuilds64.antrophic.api"
API_KEY = API_KEY_PATH.read_text().strip()
client = anthropic.Anthropic(api_key=API_KEY)

# --- Pfade ---
BRAND_CONTENT = Path.home() / "ChrisBuilds64" / "brand" / "content"
CONTROL_DIR = Path.home() / "ChrisBuilds64" / "control"

# --- Tool Definitionen (JSON Schema fuer Claude) ---

tools = [
    {
        "name": "list_day_files",
        "description": "Lists all files in a DAY-XXX content package folder. Returns filenames and sizes. Use this FIRST to see what's available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "day_number": {
                    "type": "integer",
                    "description": "The DAY number (e.g. 32 for DAY-032)",
                }
            },
            "required": ["day_number"],
        },
    },
    {
        "name": "read_file",
        "description": "Reads the content of a specific file from a DAY package. Use after list_day_files to read individual files for review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "day_number": {
                    "type": "integer",
                    "description": "The DAY number",
                },
                "filename": {
                    "type": "string",
                    "description": "The filename to read (e.g. 'linkedin-post.txt', 'substack.md', 'meta.json')",
                },
            },
            "required": ["day_number", "filename"],
        },
    },
    {
        "name": "load_content_rules",
        "description": "Loads the official content rules and boundaries. These define what makes a good post, format requirements, and publishing guidelines. Call this to understand the quality standards.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# --- Tool Implementierungen ---

def find_day_folder(day_number: int) -> Path | None:
    """Findet den DAY-XXX Ordner (Name kann Slug enthalten)."""
    pattern = f"DAY-{day_number:03d}*"
    matches = list(BRAND_CONTENT.glob(pattern))
    return matches[0] if matches else None


def list_day_files(day_number: int) -> str:
    folder = find_day_folder(day_number)
    if not folder:
        return f"ERROR: No folder found for DAY-{day_number:03d}"

    files = []
    for f in sorted(folder.iterdir()):
        if f.name.startswith("."):
            continue
        size = f.stat().st_size
        # Skip binary files
        if f.suffix in [".png", ".jpg", ".jpeg", ".gif"]:
            files.append(f"{f.name} ({size:,} bytes) [IMAGE - not readable]")
        else:
            files.append(f"{f.name} ({size:,} bytes)")

    return f"Folder: {folder.name}\n\nFiles:\n" + "\n".join(f"- {f}" for f in files)


def read_file(day_number: int, filename: str) -> str:
    folder = find_day_folder(day_number)
    if not folder:
        return f"ERROR: No folder found for DAY-{day_number:03d}"

    filepath = folder / filename
    if not filepath.exists():
        return f"ERROR: File not found: {filename}"

    if filepath.suffix in [".png", ".jpg", ".jpeg", ".gif"]:
        return "ERROR: Cannot read binary image files"

    content = filepath.read_text(encoding="utf-8")
    # Truncate very long files
    if len(content) > 8000:
        content = content[:8000] + f"\n\n[... TRUNCATED, total {len(content)} chars]"
    return content


def load_content_rules() -> str:
    """Laedt Content Boundaries + Hierarchy Regeln."""
    rules = []

    # Content Boundaries
    boundaries_path = CONTROL_DIR / "principles" / "CONTENT-BOUNDARIES.md"
    if boundaries_path.exists():
        rules.append("=== CONTENT BOUNDARIES ===\n" + boundaries_path.read_text())

    # CLAUDE.md Content Section (extract relevant parts)
    rules.append("""=== CONTENT HIERARCHY (DEFINITIVE) ===

Stufe 1: Substack = MASTER CONTENT (detailed, logbook format, written FIRST)
Stufe 2: LinkedIn Post = Independent narrative (same core, different form, NOT compressed Substack)
Stufe 3: LinkedIn Article = Substack format adapted for LinkedIn (2-5 days after Post)
Stufe 4+: TikTok/Instagram = Attention only

Rule: Substack = Source. Everything else = Derivative. Never reversed.

=== SUBSTACK FORMAT ===
- LOGBOOK ENTRY header (Date, Location, Time, Weather, Mood, Track)
- Section headers: ALWAYS CAPS
- Sign-off: --Chris
- Outro: Day number, bio, subscribe link

=== LINKEDIN POST ===
- Independent narrative (NOT copy-paste compression)
- Must deliver standalone value
- No link in post body (link in First Comment only)
- No teaser tone ("want more? Go to Substack")
- Max 3000 chars

=== FIRST COMMENT ===
- Curiosity or Identification hook
- NEVER just "full article here"

=== DALL-E PROMPT ===
- Creative + varied (never "man at laptop")
- Visual metaphor for article core
- ALWAYS 16:9
- Space for title overlay top-left
""")

    return "\n\n".join(rules)


# --- Tool Dispatcher ---

def execute_tool(name: str, input_data: dict) -> str:
    """Fuehrt das angeforderte Tool aus."""
    if name == "list_day_files":
        return list_day_files(input_data["day_number"])
    elif name == "read_file":
        return read_file(input_data["day_number"], input_data["filename"])
    elif name == "load_content_rules":
        return load_content_rules()
    else:
        return f"ERROR: Unknown tool: {name}"


# --- System Prompt (gleich wie 02, aber kuerzer -- die Regeln kommen per Tool) ---

SYSTEM_PROMPT = """You are a Content QA Analyst for the brand "ChrisBuilds64".

Your job: Review a complete DAY-XXX content package before publishing.

## Workflow
1. FIRST: Load the content rules (load_content_rules)
2. THEN: List all files in the DAY package (list_day_files)
3. THEN: Read each relevant file (read_file) -- skip images and HTML duplicates
4. FINALLY: Give your structured review

## Review Output Format
For each deliverable, give:
- Format compliance (pass/fail with details)
- Quality score (1-10)
- Issues found
- Specific fix suggestions

End with:
- Overall package score
- Top 3 improvements
- Publish recommendation (READY / NEEDS WORK / HOLD)

Be direct. Be critical. No fluff.
"""


# --- DER AGENT LOOP ---

def run_agent(day_number: int):
    messages = [
        {
            "role": "user",
            "content": f"Review the complete content package for DAY-{day_number:03d}. Check all deliverables.",
        }
    ]

    print(f"Content QA Agent reviewing DAY-{day_number:03d}...")
    print("=" * 60)

    iteration = 0
    max_iterations = 15  # Safety: Agent darf max 15 Loops machen

    while iteration < max_iterations:
        iteration += 1

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Fertig?
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(block.text)
            break

        # Tool Calls verarbeiten
        tool_results = []

        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"\n[Agent thinks]: {block.text[:200]}...")

            elif block.type == "tool_use":
                print(f"[Tool Call #{iteration}]: {block.name}({json.dumps(block.input)})")

                result = execute_tool(block.name, block.input)

                # Nur erste 200 Zeichen vom Result anzeigen (sonst wird's unlesbar)
                preview = result[:200].replace("\n", " ")
                print(f"[Result]: {preview}...")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        # Messages updaten
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    print()
    print("=" * 60)
    print(f"Agent fertig nach {iteration} Iterationen")
    print(f"Nachrichten in der Conversation: {len(messages)}")


# --- Run ---
if __name__ == "__main__":
    run_agent(32)
