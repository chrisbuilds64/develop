"""
Content QA Analyst Agent (AG-001)

Spec: specs/AG-001_content-qa-analyst.md

Usage:
    python content_qa_agent.py 32              # Review DAY-032
    python content_qa_agent.py 30 31 32        # Review multiple DAY packages
    python content_qa_agent.py 32 --focus linkedin-post
    python content_qa_agent.py all             # Review ALL DAY packages

Results saved to: results/YYYY-MM-DD_DAY-XXX_qa-review.md
"""

import anthropic
import json
import sys
from datetime import datetime
from pathlib import Path

# --- Config ---

API_KEY_PATH = Path.home() / ".secrets" / "chrisbuilds64" / "chrisbuilds64.antrophic.api"
BRAND_CONTENT = Path.home() / "ChrisBuilds64" / "brand" / "content"
CONTROL_DIR = Path.home() / "ChrisBuilds64" / "control"
RESULTS_DIR = Path(__file__).parent / "results"
MODEL = "claude-sonnet-4-5-20250929"
MAX_ITERATIONS = 15


# --- System Prompt (generated from Spec) ---

SYSTEM_PROMPT = """You are a Content QA Analyst for the brand ChrisBuilds64.

## YOUR ROLE
Senior Content Strategist with 15 years of social media experience. You specialize in LinkedIn and newsletter publishing. You know the ChrisBuilds64 brand rules by heart and review content packages before publication.

## YOUR GOAL
Review a complete DAY-XXX content package. Deliver a structured QA report with a clear publish recommendation.

## BRAND CONTEXT
Christian Moser, 61, IT veteran (40 years experience). Former Oracle DBA and SAP consultant, now AI strategy advisor. Building in public since December 2025. Tone: Direct, humorous, self-deprecating, technically grounded but accessible.

## WORKFLOW
1. Load content rules (load_content_rules) -- ALWAYS FIRST
2. List all files in the DAY package (list_day_files)
3. Read EVERY text deliverable (read_file) -- skip images and HTML duplicates
4. Deliver your review

## OUTPUT FORMAT (FOLLOW EXACTLY)

```
# QA REVIEW: DAY-XXX -- [Title from meta.json]

## CHECKLIST
| Deliverable | Status | Score |
|-------------|--------|-------|
| substack.md | PASS/FAIL | X/10 |
| linkedin-post.txt | ... | ... |
| first-comment.txt | ... | ... |
| linkedin-article.txt | ... | ... |
| tiktok-script.txt | ... | ... |
| dalle-prompt.txt | ... | ... |
| meta.json | ... | ... |
| title-dark.svg | ... | ... |
| title-light.svg | ... | ... |

## FINDINGS

### Substack
[Format check against Logbook rules. Quote specific lines.]

### LinkedIn Post
[Independence check. Hook quality. Standalone value.]

### First Comment
[Hook type: Curiosity or Identification? Never "full article here".]

### LinkedIn Article
[Adaptation quality. Consistency with Substack.]

### TikTok Script
[Teleprompter-ready? Caption present?]

### DALL-E Prompt
[Creative? NOT "man at laptop"? 16:9? Space for title overlay?]

### Meta.json
[All fields present? Consistent with actual files?]

### Title Overlays
[Both dark and light versions present?]

## CROSS-CHECK
[Do all pieces tell the same core story? Any contradictions?]

## TOP 3 FIXES
1. [Most important fix with concrete suggestion]
2. [Second fix]
3. [Third fix]

## VERDICT: [READY / NEEDS WORK / HOLD]
[1-2 sentence justification]
```

## RULES

### You MUST:
- Load content rules FIRST before reading any files
- Read ALL text deliverables (never skip one)
- Check Substack against Logbook format (LOGBOOK ENTRY header, CAPS section headers, --Chris sign-off)
- Check LinkedIn Post is an INDEPENDENT narrative (not compressed Substack)
- Check First Comment hook type (Curiosity/Identification, NEVER "full article here")
- Check meta.json consistency with actual file inventory
- Quote specific lines when reporting issues
- Give exactly 3 top fixes, prioritized

### You MUST NOT:
- Modify any files (read-only)
- Analyze images (text files only)
- Give vague praise ("Great job!" is forbidden)
- Suggest changes that alter the brand's core tone
- List more than 3 top fixes
- Read HTML versions (they duplicate .txt/.md content)
"""


# --- Tools: Definitions ---

TOOLS = [
    {
        "name": "list_day_files",
        "description": "Lists all files in a DAY-XXX content package folder. Returns filenames with sizes and type markers. Use this to see what deliverables exist.",
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
        "description": "Reads a specific file from a DAY content package. Returns file content as text. Use after list_day_files to read individual deliverables.",
        "input_schema": {
            "type": "object",
            "properties": {
                "day_number": {
                    "type": "integer",
                    "description": "The DAY number",
                },
                "filename": {
                    "type": "string",
                    "description": "Filename to read (e.g. 'linkedin-post.txt', 'substack.md', 'meta.json')",
                },
            },
            "required": ["day_number", "filename"],
        },
    },
    {
        "name": "load_content_rules",
        "description": "Loads the official ChrisBuilds64 content rules: Content Hierarchy, Format Requirements, Publishing Guidelines, and Content Boundaries. Call this FIRST before reviewing any content.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# --- Tools: Implementations ---

def find_day_folder(day_number: int) -> Path | None:
    pattern = f"DAY-{day_number:03d}*"
    matches = list(BRAND_CONTENT.glob(pattern))
    return matches[0] if matches else None


def tool_list_day_files(day_number: int) -> str:
    folder = find_day_folder(day_number)
    if not folder:
        return f"ERROR: No folder found for DAY-{day_number:03d}"

    files = []
    for f in sorted(folder.iterdir()):
        if f.name.startswith("."):
            continue
        size = f.stat().st_size
        if f.suffix in [".png", ".jpg", ".jpeg", ".gif"]:
            files.append(f"{f.name} ({size:,} bytes) [IMAGE]")
        else:
            files.append(f"{f.name} ({size:,} bytes)")

    return f"Folder: {folder.name}\n\nFiles:\n" + "\n".join(f"- {f}" for f in files)


def tool_read_file(day_number: int, filename: str) -> str:
    folder = find_day_folder(day_number)
    if not folder:
        return f"ERROR: No folder found for DAY-{day_number:03d}"

    filepath = folder / filename
    if not filepath.exists():
        return f"ERROR: File not found: {filename}"

    if filepath.suffix in [".png", ".jpg", ".jpeg", ".gif"]:
        return "ERROR: Cannot read binary image files"

    content = filepath.read_text(encoding="utf-8")
    if len(content) > 8000:
        content = content[:8000] + f"\n\n[... TRUNCATED at 8000 chars, total {len(content)}]"
    return content


def tool_load_content_rules() -> str:
    rules = []

    boundaries_path = CONTROL_DIR / "principles" / "CONTENT-BOUNDARIES.md"
    if boundaries_path.exists():
        rules.append("=== CONTENT BOUNDARIES ===\n" + boundaries_path.read_text())

    rules.append("""=== CONTENT HIERARCHY (NON-NEGOTIABLE) ===

1. Substack = MASTER CONTENT (detailed, logbook format, written FIRST)
2. LinkedIn Post = Independent narrative (same core, different form, NOT compressed Substack)
3. LinkedIn Article = Substack format adapted for LinkedIn (2-5 days after Post)
4. TikTok/Instagram = Attention only

Rule: Substack = Source. Everything else = Derivative. Never reversed.

=== SUBSTACK FORMAT ===
- LOGBOOK ENTRY header (Date, Location, Time, Weather, Mood, Track)
- Section headers: ALWAYS CAPS (## THE SETUP, ## THE PUNCHLINE)
- Sign-off: --Chris (em dash, not double hyphen)
- Outro: Day number, bio, subscribe link

=== LINKEDIN POST ===
- Independent narrative (NOT copy-paste compression of Substack)
- Must deliver standalone value
- No link in post body (link goes in First Comment)
- No teaser tone ("want more? Go to Substack" = FORBIDDEN)
- Max 3000 characters

=== FIRST COMMENT ===
- Must be Curiosity or Identification hook
- NEVER just "full article here" or "link to Substack"

=== DALL-E PROMPT ===
- Creative and varied (NEVER "man at laptop" or similar cliche)
- Visual metaphor for the article's core idea
- ALWAYS 16:9 aspect ratio
- Space for title overlay top-left (negative space)

=== META.JSON REQUIRED FIELDS ===
day, title, subtitle, slug, created, publish_date, track, tags, linkedin_article, content_boundaries_checked
""")

    return "\n\n".join(rules)


TOOL_DISPATCH = {
    "list_day_files": lambda args: tool_list_day_files(args["day_number"]),
    "read_file": lambda args: tool_read_file(args["day_number"], args["filename"]),
    "load_content_rules": lambda args: tool_load_content_rules(),
}


# --- Agent Loop ---

def run_agent(client: anthropic.Anthropic, day_number: int, focus: str | None = None) -> str:
    """Run the QA agent for a single DAY package. Returns the review as string."""
    prompt = f"Review the complete content package for DAY-{day_number:03d}."
    if focus:
        prompt += f" Focus especially on: {focus}"

    messages = [{"role": "user", "content": prompt}]
    review_text = ""

    print(f"\n  Reviewing DAY-{day_number:03d}...", end="", flush=True)

    for iteration in range(1, MAX_ITERATIONS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    review_text += block.text
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_DISPATCH.get(block.name)
                if handler:
                    result = handler(block.input)
                else:
                    result = f"ERROR: Unknown tool: {block.name}"

                print(".", end="", flush=True)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    print(f" done ({iteration} iterations)")
    return review_text


def save_result(day_number: int, review: str) -> Path:
    """Save review to results/ as Markdown file."""
    RESULTS_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}_DAY-{day_number:03d}_qa-review.md"
    filepath = RESULTS_DIR / filename
    filepath.write_text(review, encoding="utf-8")
    return filepath


def discover_all_days() -> list[int]:
    """Find all DAY-XXX folders and return their numbers, sorted."""
    days = []
    for folder in BRAND_CONTENT.iterdir():
        if folder.is_dir() and folder.name.startswith("DAY-"):
            try:
                num = int(folder.name.split("-")[1])
                days.append(num)
            except (IndexError, ValueError):
                continue
    return sorted(days)


# --- CLI ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python content_qa_agent.py 32              # Review DAY-032")
        print("  python content_qa_agent.py 30 31 32        # Review multiple")
        print("  python content_qa_agent.py all              # Review ALL packages")
        print("  python content_qa_agent.py 32 --focus post  # Focus area")
        print()
        print(f"Results saved to: {RESULTS_DIR}/")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=API_KEY_PATH.read_text().strip())

    # Parse focus flag
    focus = None
    args = sys.argv[1:]
    if "--focus" in args:
        idx = args.index("--focus")
        if idx + 1 < len(args):
            focus = args[idx + 1]
        args = args[:idx]  # Remove --focus and value from day args

    # Parse day numbers
    if args[0].lower() == "all":
        days = discover_all_days()
        print(f"Discovered {len(days)} DAY packages")
    else:
        days = [int(d) for d in args]

    # Run reviews
    print(f"Content QA Analyst -- {len(days)} package(s) to review")
    print("=" * 60)

    results = []
    for day in days:
        review = run_agent(client, day, focus)
        filepath = save_result(day, review)
        results.append((day, filepath))

    # Summary
    print()
    print("=" * 60)
    print(f"COMPLETE: {len(results)} review(s) saved")
    print()
    for day, path in results:
        print(f"  DAY-{day:03d} -> {path.name}")
    print()
    print(f"Results directory: {RESULTS_DIR}")
