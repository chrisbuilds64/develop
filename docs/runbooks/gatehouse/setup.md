# Runbook: Setting up Gatehouse at a client

**Audience:** the operator who will run the interview.
**When:** before the first session with the client, never on the day.
**Time:** 30–60 minutes, most of it waiting on the client's IT.

This runbook exists because the setup is the part that fails in front of
people. Everything here is meant to be done in an empty room.

---

## 0. Before you touch anything

Three questions the client has to answer first. If any is open, stop and
settle it — do not start and hope.

| Question | Why it blocks |
|---|---|
| Where may the model run? | Determines whether this is a hosted or an on-premise install. Everything else follows. |
| What may be sent to it? | The interview contains their answers about their own weak points. Someone has to say that is acceptable. |
| Where do the answers live afterwards? | They belong in the client's version control, not on your laptop. |

Write the answers down. They are the first three entries of the client's
canon, before a single question has been asked.

---

## 1. Version control first

The instance directory is the record of the engagement. It goes under
version control before the first run, not after.

If the client has version control, use theirs. If not, this is the
moment to set it up with them — an auditable system needs a history, and
a directory nobody versions is a directory that quietly changes.

```bash
mkdir -p <instance-path>
cd <instance-path> && git init      # only if the client has nothing
```

---

## 2. Install

Python 3.11 or newer. No build step, no database, no container required.

```bash
cd apps/gatehouse
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## 3. Configure

```bash
cp gatehouse.example.toml gatehouse.toml
```

Set three things:

- `[pack] path` — the canon pack. Not part of this repository; you bring it.
- `[instance] path` — the directory from step 1.
- `[model]` — profiles and task routing, see below.

`gatehouse.toml` is never committed. It points at the private pack and may
name a credential variable.

---

## 4. Credentials

**Gatehouse reads no key and writes no key.** It constructs a bare client
and the SDK resolves whatever the machine offers, in this order:

1. `ANTHROPIC_API_KEY`
2. `ANTHROPIC_AUTH_TOKEN`
3. a signed-in profile on disk
4. workload identity

Prefer the client's existing arrangement over introducing a new one. In
most cases that means an environment variable their IT already manages.

Two rules that are not negotiable:

- **The key never goes into `gatehouse.toml`.** The configuration names a
  variable at most; it never carries a value.
- **The key never goes into shell history.** Load it from wherever the
  client keeps secrets, in a script that reads the file — do not type
  `export ANTHROPIC_API_KEY=sk-...` at a prompt.

A launcher that reads the key from a file and starts the program is the
usual shape:

```bash
#!/usr/bin/env bash
set -euo pipefail
export ANTHROPIC_API_KEY="$(< /path/to/the/clients/secret/file)"
exec .venv/bin/python -m gatehouse gatehouse.toml "$@"
```

Keep that script out of version control — it encodes one client's paths.

If the client will run a model in their own house, none of this applies:
use the `openai_compat` adapter with their `base_url`, set `local = true`,
and there is no credential to manage.

---

## 5. Choose which model does what

Not every task warrants the strongest model. Follow-up questions during
an interview are many small calls; a synthesis is one call where
reasoning quality decides the result.

```toml
[model]
default = "strong"

[model.tasks]
followup = "fast"
```

This is a cost decision, and it is the client's. Record the reasoning
next to the choice — a routing table without a reason is a price list,
not a decision someone can defend later.

---

## 6. Check, in an empty room

```bash
.venv/bin/python -m gatehouse gatehouse.toml --check
```

It loads the pack, prints the routing, and makes one real call per
profile. Expected:

```
Pack     OK      <pack name> (N Blöcke, M Fragen)
Instanz  OK      <instance path>
Aufgabe  followup     -> fast (claude-haiku-4-5)
Profil   OK      fast: claude-haiku-4-5 erreichbar
Bereit.
```

| Failure | What it means |
|---|---|
| `Pack ... FEHLER` | Wrong path, or the pack is not where you think. |
| `Keine Anmeldung gefunden` | No credential the SDK can see. A Claude Code login does not count — it is a separate sign-in this program cannot use. |
| `... ist nicht gesetzt` | The configuration names a variable that the launcher did not export. |
| `nicht erreichbar` | Network or endpoint. If on-premise: is their model actually running? |

Do not proceed to a client session on a red check.

---

## 7. Run

```bash
.venv/bin/python -m gatehouse gatehouse.toml
```

Open the printed address. The start page names every destination answers
can reach — read it out loud to the client before the first question. It
takes ten seconds and it is the difference between informed and assumed
consent.

---

## 8. After the first block, not at the end

Open `/audit` once, early. It lists every call: which task, which
profile, which model, how many characters and tokens left the machine.

Checking it after the first block, while there is still time to change
something, is the whole point. Checking it at the end is a post-mortem.

Commit the instance directory when the session ends.

---

## Known gaps

Honest list, so nobody discovers these in front of a client:

- **Recovery from a bad answer** is by editing the answer and resubmitting.
  There is no undo history beyond the client's own version control.
- **One run per instance directory.** A second run overwrites the first
  unless you point at a new directory.
- **No cost display in money.** Tokens are recorded per call; converting
  them to currency is not built.
