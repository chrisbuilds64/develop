# ADR-016: Public Demo Runs the Real Core With a Sandbox per Visitor

**Status:** Proposed
**Date:** 2026-10-21

---

## Context

An audience should open the product on their own phones and click through a working case, not a mock-up. Many visitors may arrive at once.

## Decision

- The demo runs the same core and surface as production, with demo configuration and fictional cases only.
- Each visitor gets a sandbox: a copy of a template folder under `demo-sessions/<random id>/`, bound to a cookie. "Start over" creates a new one. Sandboxes expire after 24 hours; a cap removes the oldest first.
- No sign-in, no real names, no tracking. Uploads stay inside the sandbox, limited in type and size. A per-IP rate limit protects the host.
- Agent results in the public demo are prepared and replayed with a short delay; live agent runs only in an operator-led session with a cost cap.

## Consequences

- What the audience sees is the real step transaction and turn logic, not a simulation.
- Real data is never readable from the demo deployment.
