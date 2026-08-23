# Gatehouse

Canon elicitation harness. Runs on client hardware, asks the questions a
canon pack defines, and writes the answers into a directory the client
owns and versions.

See `docs/use-cases/UC-AG-004_gatehouse.md` for scope,
`docs/adr/ADR-010` for the runtime constraints and `docs/adr/ADR-011`
for the model adapter.

## What it is not

Gatehouse holds no questions. The canon pack does, and the pack is not
in this repository. Without one, this code starts and asks nothing.

It also does not read the client's files, code or history. Elicitation
is data-poor by design; system analysis is a separate stage with a
different risk profile.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp gatehouse.example.toml gatehouse.toml   # set pack and instance paths
python -m gatehouse gatehouse.toml
```

Open `http://127.0.0.1:8100`.

The default configuration uses the `echo` adapter, which sends nothing
anywhere and returns no follow-up questions. That is deliberate: the
whole flow can be walked, and shown to a client, before anyone has
agreed which model may see their answers.

## Model

Three adapters: `echo` (no model), `anthropic` (Claude via API),
`openai_compat` (anything speaking the OpenAI chat shape, which covers
most on-premise runtimes).

API keys are read from environment variables named in the config, never
from the config file itself.

Every outbound call is written to `audit.jsonl` in the instance
directory before it is sent, and is visible at `/audit`.

## What a run produces

In the instance directory:

- `run.json` — state, machine-owned
- `interview.md` — the same content for humans, rewritten on every answer
- `audit.jsonl` — every model call

All three belong in the client's version control.

## Pack format

See `packs/example/pack.toml`. It is a format demonstration, not the
real pack.

A pack holds stage directions, ordered blocks with questions and exit
criteria, and follow-up triggers. The triggers are the substance: a bare
list of questions produces a survey, not an interview.
