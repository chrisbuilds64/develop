# services/oracle/

Oracle Database 23ai Free — schema, migrations, and seed data.

## Container Runtime Options

| Option | License | Daemon | Rootless | Notes |
|---|---|---|---|---|
| **Docker Desktop** | Free for personal/edu; paid for companies >250 users or >$10M revenue | Yes | No | Current choice — simplest setup, GUI available |
| **Colima** | MIT (open source) | No (VM-based) | Yes | Drop-in Docker CLI replacement for macOS, no license concern for GmbH |
| **Podman** | Apache 2.0 (Red Hat) | No (daemonless) | Yes by default | Most secure, rootless containers, CLI-compatible with Docker |
| **OrbStack** | Free for personal; paid for commercial | Yes | No | Fast macOS alternative to Docker Desktop, commercial license required |

**Current choice:** Docker Desktop (training/demo use only, no production rollout).
**Recommended alternative:** Colima or Podman when commercial license compliance is needed.

## Oracle Container Registry

Registry: `container-registry.oracle.com`
Image: `container-registry.oracle.com/database/free:latest-lite`

**Authentication (post June 30, 2025):**
SSO passwords no longer accepted. Use an Auth Token:
1. Login at https://container-registry.oracle.com
2. Generate Auth Token under User Settings
3. Store token: `~/.secrets/chrisbuilds64/oracle-registry.token` (chmod 400)
4. `docker login container-registry.oracle.com -u YOUR_EMAIL -p $(cat ~/.secrets/chrisbuilds64/oracle-registry.token)`

**License acceptance required** before pulling:
- Login at container-registry.oracle.com → database/free → Accept License

## Local Development Setup

```bash
# Start Oracle 23ai Free locally
docker compose up -d

# Wait for database to be ready (2-3 minutes)
docker logs -f oracle-free | grep "DATABASE IS READY"

# Connect via SQL*Plus
docker exec -it oracle-free sqlplus system/YourPassword@FREEPDB1
```

## Approach

Migration-based deployment using **Liquibase** via **Oracle SQLcl**.

Two categories of database objects:

| Type | Examples | Deployment |
|---|---|---|
| Stateful (run once) | Tables, indexes, sequences, constraints | `releases/YYYY.MM/` — versioned, never modified |
| Stateless (repeatable) | Packages, procedures, views, triggers | `packages/`, `views/` etc. — `CREATE OR REPLACE` on every deploy |

## Planned Structure

```
oracle/
├── docker-compose.yml      # Local Oracle 23ai Free
├── controller.xml          # Master Liquibase changelog
├── liquibase.properties    # Connection config (per environment via env vars)
├── releases/               # Versioned, immutable changesets (DDL, migrations)
│   └── 2026.01/
├── packages/               # PL/SQL packages (idempotent)
├── views/
├── triggers/
├── seed/                   # Reference data
└── tests/                  # utPLSQL test packages
```

## Phase

Phase 1 — local Oracle 23ai Free running in Docker.
