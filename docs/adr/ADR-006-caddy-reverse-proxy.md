# ADR-006: Caddy as Reverse Proxy

**Status:** Accepted
**Date:** 2026-07-19
**Provenance:** First explicit record of a decision that production reality had already made. Caddy was running live on the production server before this document existed; the competing Traefik setup (archived `chrisbuilds64/sdlc`) never reached production. Formalized 2026-07-19 during repo consolidation.

---

## Context

The production server is a single host running Docker. It needs one reverse proxy terminating TLS for multiple services: the backend API (`api.chrisbuilds64.com`) and the feldorakel app (`.com` and `.dev` domains).

Two candidates existed in parallel, in two repos:

- **Caddy** — deployed via this repo's `infra/ansible/docker-caddy.yml`, live on ports 80/443.
- **Traefik** — planned in the `sdlc` repo, playbook fully written, never deployed.

The 2026-07-19 repo consolidation (one repo, one proxy playbook) forced the implicit choice to become explicit.

## Decision

Caddy 2 (`caddy:2-alpine` container) is the reverse proxy. Static Caddyfile with one block per domain, automatic TLS via Let's Encrypt, JSON logs to stdout. The Traefik playbook was deliberately not migrated and remains conserved in the archived `sdlc` repo.

## Alternatives

**Traefik** was the real alternative on the table. Its strengths: dynamic routing via container labels (services register themselves), built-in dashboard, rich middleware ecosystem. Its cost: routing rules live as labels scattered across compose files, plus a more complex static/dynamic config split.

## Why Caddy

- **Server reality.** Caddy was already serving three live routes in production. Traefik existed only as a playbook. Promoting the proven-working option is cheaper and less risky than deploying the planned one.
- **Fit to scale.** At single-host, three-route scale, a static Caddyfile is readable at a glance. Traefik's dynamic service discovery buys nothing here — there is no service churn to discover.
- **TLS with zero ceremony.** Caddy's automatic Let's Encrypt handling requires no acme.json, no cert resolver config.

## Consequences

**Benefits:**
- One config file (`/opt/caddy/Caddyfile`, templated in `docker-caddy.yml`) shows the complete public routing surface of the server.
- Adding a route is an explicit, reviewable change to the playbook — routing changes go through Git.

**Trade-offs:**
- No automatic service discovery. Every new service needs a template edit and a deploy.
- A static template can drift from server reality. This is not hypothetical: during the 2026-07-19 consolidation deploy, the live Caddyfile had three routes while the template knew only one — undetected, the deploy would have deleted two live routes. Mitigation: the template in `infra/ansible/docker-caddy.yml` is the single source of truth; any change made on the server must land in the template in the same step.
