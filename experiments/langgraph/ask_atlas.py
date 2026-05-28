"""
ask_atlas.py — Direct Atlas query
ChrisBuilds64 // 2026-05-28

Ask Atlas a question directly. No Axel, no flow, no Chris Gate.
Atlas responds with his full signature + shared context loaded.

Model: gpt-4o (not mini — direct conversations deserve the full model)

Usage:
    .venv/bin/python ask_atlas.py "Your question here"
    .venv/bin/python ask_atlas.py  # interactive mode
"""

import sys
from pathlib import Path
import openai
from context_loader import load_agent_context

OPENAI_KEY = (Path.home() / ".secrets/chrisbuilds64/openai.api").read_text().strip()
gpt = openai.OpenAI(api_key=OPENAI_KEY)


def ask_atlas(question: str) -> str:
    context = load_agent_context("atlas", budget=10000)

    system_prompt = f"""{context}

You are responding directly to Chris — the human authority in this system.
Respond as Atlas: strategic, architectural, calm, precise.
Do not introduce yourself. Do not explain your role. Just answer.
If the question touches on implementation detail, elevate it to the system level.
If you disagree with an implied assumption, say so directly."""

    response = gpt.chat.completions.create(
        model="gpt-4o",
        max_completion_tokens=800,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"\nAtlas:\n{'-' * 40}")
        print(ask_atlas(question))
        print()
    else:
        print("Atlas — direct query (type 'exit' to quit)\n")
        while True:
            question = input("You: ").strip()
            if question.lower() in ("exit", "quit", "q"):
                break
            if not question:
                continue
            print(f"\nAtlas:\n{'-' * 40}")
            print(ask_atlas(question))
            print()
