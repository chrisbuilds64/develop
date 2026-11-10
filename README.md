# chrisbuilds64/develop

The development system of ChrisBuilds64, built in public.

The product here is **casefile**, a case that runs itself, and the **cockpit**, the surface people work in. One core
carries every application. What one application differs from another in — stages, deliverables, words, people —
is configuration, not code.

## What is where

| Path | What it is |
|---|---|
| `apps/casefile/` | The core. A case is a folder, its stage folder is its status, one core writes on everyone's behalf. Also the web surface (`web/`) and one configuration per domain (`config/<domain>/`). |
| `apps/cockpit/` | The surface over the core: one sign-in, workspaces, accounts with their own AI subscription, an agent panel beside every case. |
| `apps/mailsort/` | Mail pre-sorting. Exploration, moves nothing yet. |
| `services/oracle/` | Oracle Database Free: schema, migrations, seed data for the Oracle demo. |
| `infra/pressroom/` | `pressroom-env`: development, test and production on one server, described in one file. |
| `infra/ansible/` | Server provisioning and hardening. |
| `sandbox/` | The whole system offline on one Mac, with fictional sample worlds. |
| `tools/` | Guards the checks run: design values only go down, the core imports no adapter or web framework. |
| `docs/adr/` | Architecture decisions, one home for all. |
| `docs/requirements/`, `docs/adr/`, `docs/GATE-CHECKLIST.md` | The requirements chain: a case's task → requirement lines (REQ) → decision record (ADR) → pull request → gate protocol. Operations runbooks live beside their code (`infra/pressroom/README.md`). |

## Run it

The quickest way is the sandbox: everything offline, fictional data, `reset` brings it back.

```bash
python3.12 sandbox/sandbox.py setup   # once, needs the network
python3 sandbox/sandbox.py up         # http://127.0.0.1:8200
python3 sandbox/sandbox.py check      # play every demo flow headless
```

Details in [sandbox/SANDBOX.md](sandbox/SANDBOX.md). Tests per application:

```bash
cd apps/casefile && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/python -m pytest -q
```

## How changes get in

No one pushes to `main`, the owner included. Every change is a pull request with green checks, merged by the product
owner. Releases are tags (`YYYY.MM.N`) that travel through development, test and production. The whole way:
[CONTRIBUTING.md](CONTRIBUTING.md).

## Earlier work

The FastAPI item service, the tweight and PressRoom Flutter apps, Feldorakel and the LangGraph experiments were
removed on 2026-11-08. Their last state is tag `archive/2026-11-08-legacy`.

## Building in public

- [Substack](https://chrisbuilds64.substack.com)
- [LinkedIn](https://linkedin.com/in/chrisbuilds64)
- [TikTok](https://tiktok.com/@chrisbuilds64)

## License

MIT — see [LICENSE](LICENSE).
