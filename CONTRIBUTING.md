# Working together on this repository

A small team: two people, each working with their own AI agents, one public repository, three stages
(development, test, production). This is how a change gets from an idea to production. It applies to everyone the
same way — no one pushes to `main` directly, the owner included.

Version 0.1, 2026-11-08. It will change as we learn; changes to this file go through a pull request like any other.

## Roles

| Role | Responsible for |
|---|---|
| Product and release | what gets built, merging into `main`, every step towards production, accepting ADRs |
| Surface and design system | `apps/*/web/src`, tokens, `DESIGN.md`, cockpit templates |
| Core, security, operations | domain logic, API, rights, data on disk, deployment, servers, the worlds shown live |

**Agents write code; people own it.** Whoever commits a change owns it — understands it, watches it, fixes it.
"The AI wrote it" is not an owner.

Anyone may work anywhere. A change in someone else's area gets that person's review — in both directions.

## The way of a change

```
task → branch from main → small commits → pull request → checks → review → approval → main
     → tag → development → test → production
```

1. **Task.** Written down where both of us see it. Large pieces are cut before they are built.
2. **Branch.** `<name>/<topic>`, from the current `main`. Lives days, not weeks. Bring `main` in daily.
3. **Pull request.** The pull request *is* the hand-over — not a mail, not a chat message. Use the template: what and
   why, decisions, what was checked and what was not.
4. **Checks** (`.github/workflows/ci.yml`): both test suites, design guard, architecture guard, the surface builds,
   the sample flows headless. Green on a fresh machine, not only on one laptop.
5. **Review.** Core changes are reviewed against the software principles (ownership, tests against the spec,
   security, explicit architecture decisions). Surface changes against the design system. Findings are review
   comments; the author fixes them.
6. **Approval and merge.** By the product owner. `main` is protected: pull request and green checks required.
7. **Release.** A tag on `main` (`YYYY.MM.N`, e.g. `2026.11.1`). Only tags travel through the stages, so every stage
   says which version it runs.
8. **Stages.** Development (both see it, real agents) → test (production data, cloned) → production. Each step is
   accepted by the product owner. The way back is always the previous tag.

## When an ADR

A new capability, a new interface, a change to rights, to how data is stored on disk, or to who may do what. The
ADR comes with the pull request, status *Proposed*; the product owner sets *Accepted*.

**Every ADR states its prior art.** casefile starts from its own abstraction and keeps it; other systems are brought
in where a domain calls for them (Git in software, never in a content workspace). So each new mechanism is held
against BPM, Git and its code hosts, and comparable systems, and placed in one of three kinds:

- **Stand apart** — nothing comparable exists; this is where the product is.
- **Use alongside** — the other system is the source for these facts; the case reads and links them, never copies them.
- **Duplicate on purpose** — a counterpart exists and we build our own anyway, with the reason written down. Bringing
  in another system is not always wanted.

An ADR without the section *Prior art* is not accepted. Template: [`docs/adr/TEMPLATE.md`](docs/adr/TEMPLATE.md).

## Places that conflict, and the rule for each

| Place | Rule |
|---|---|
| `apps/casefile/web/dist/` | The deploy takes the built surface from the repo. Rebuild it from your branch's source after updating from `main`; never merge it by hand. |
| `openapi.json`, `api-types.d.ts` | Generated. Regenerate after updating from `main`, never merge by hand. |
| `tools/design_guard.baseline.json` | A ratchet: the number of raw values may go down, never up. |
| `config/*/vocabulary.json` | Add words, do not rewrite them. Worlds shown live in German are not rewritten without agreement. |
| Test data | Everything a test needs is in the repo. A test that is green only on one machine is not green. |
| Media | No new videos or images in this repository: it is public and git forgets nothing. They go to the media hub. |

## Freeze

Before a talk or a client meeting a freeze is announced: production and the worlds shown stay as they are; work on
`main` goes on. A freeze is written in the pull request that would cross it.

## Public repository

Only fictional people, companies and cases. No credentials, no internal host names, no client names — in code,
commits, branch names, issues and pull request texts alike.
