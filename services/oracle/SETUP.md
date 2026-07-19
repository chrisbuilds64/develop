# Oracle 26ai Free — Local Development Setup

Complete step-by-step guide to get Oracle 26ai Free running locally with SQLcl and Liquibase migrations.

---

## Prerequisites

### 1. Docker Desktop (or alternative)

Install Docker Desktop: https://www.docker.com/products/docker-desktop/

**Alternatives (no commercial license required):**
| Tool | Install | Notes |
|---|---|---|
| Colima | `brew install colima docker` then `colima start` | Open source, drop-in Docker CLI replacement |
| Podman | `brew install podman` then `podman machine init && podman machine start` | Rootless by default, most secure |

This guide uses Docker Desktop. Commands are identical for Colima/Podman.

### 2. Java (required by SQLcl)

```bash
brew install openjdk
```

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
```

Verify:
```bash
java -version
# openjdk version "25.x.x"
```

### 3. SQLcl (Oracle CLI with built-in Liquibase)

```bash
brew install sqlcl
```

Add both Java and SQLcl to `~/.zshrc` (or `~/.bashrc`):
```bash
# Java (required by SQLcl)
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"

# SQLcl — check installed version first: ls /opt/homebrew/Caskroom/sqlcl/
export PATH="/opt/homebrew/Caskroom/sqlcl/26.1.0.086.1709/sqlcl/bin:$PATH"
```

Apply immediately:
```bash
source ~/.zshrc
```

Verify:
```bash
sql -v
# SQLcl: Release 26.x.x
```

**What is SQLcl?**
Oracle's official CLI tool — replaces the older SQL*Plus. It has Liquibase built in, so you don't need a separate Liquibase installation. You connect to Oracle and run `lb update` directly from within SQLcl.

**What is Liquibase?**
A migration engine for databases. It tracks which SQL changesets have already run (in a table called `DATABASECHANGELOG`) and ensures each changeset runs exactly once, in the correct order. This is the foundation of reproducible database deployment.

---

## Oracle Container Registry Setup

Oracle images require authentication and license acceptance.

### Step 1: Create an Oracle account

Register at: https://profile.oracle.com/myprofile/account/create-account.jspx

### Step 2: Accept the license

1. Go to https://container-registry.oracle.com
2. Search for `database/free`
3. Click the image → click **Continue** to accept the Oracle Free Use Terms and Conditions

You must accept this before the pull will succeed.

### Step 3: Generate an Auth Token

**Important:** Since June 30, 2025, Oracle Container Registry no longer accepts SSO passwords for CLI login. You must use an Auth Token.

1. Log in at https://container-registry.oracle.com
2. Click your username (top right) → **User Settings** or **Auth Token**
3. Generate a new token
4. Copy it immediately — it is only shown once

### Step 4: Store the token securely

```bash
# Store outside of any git repository
echo "YOUR_TOKEN_HERE" > ~/.secrets/chrisbuilds64/oracle-registry.token
chmod 400 ~/.secrets/chrisbuilds64/oracle-registry.token
```

### Step 5: Login to the registry

```bash
docker login container-registry.oracle.com \
  -u your@email.com \
  -p $(cat ~/.secrets/chrisbuilds64/oracle-registry.token)
```

---

## Starting Oracle 26ai Free Locally

```bash
cd services/oracle

# Start the container
docker compose up -d

# Watch the logs until database is ready (takes 2-3 minutes on first run)
docker logs -f oracle-free | grep -m1 "DATABASE IS READY TO USE"
```

**What happens on first start:**
Oracle initializes the database files, creates the Container Database (CDB: FREE) and the Pluggable Database (PDB: FREEPDB1). This takes 2-3 minutes. Subsequent starts are faster (data persisted in Docker volume `oracle-free-data`).

**Local dev credentials:**

| User | Password | Purpose |
|---|---|---|
| system | OracleLocal26ai | DBA — run Liquibase migrations, schema owner |
| PDBADMIN | OracleLocal26ai | PDB admin (Oracle built-in) |
| sdlc_app | SdlcApp2026 | App user — Python API connects as this user |

**Production:** Never hardcode passwords. Use environment variables or a secrets manager. The `sdlc_app` password must be rotated before any non-local deployment.

**Note on passwords:** Avoid special characters (`!`, `@`, `#`) in Oracle passwords used on the CLI. They cause shell escaping issues when connecting via `docker exec` or SQLcl.

---

## Connecting with SQLcl

```bash
# Basic connection
sql system/OracleLocal26ai@localhost:1521/FREEPDB1

# Silent mode (for scripting)
sql -s system/OracleLocal26ai@localhost:1521/FREEPDB1
```

Inside SQLcl you can run any SQL plus Liquibase commands (`lb update`, `lb status`, `lb tag`).

---

## Running Liquibase Migrations

```bash
cd services/oracle

# Check which changesets are pending
echo "lb status -changelog-file controller.xml
EXIT" | sql -s system/OracleLocal26ai@localhost:1521/FREEPDB1

# Apply all pending changesets
echo "lb update -changelog-file controller.xml
EXIT" | sql -s system/OracleLocal26ai@localhost:1521/FREEPDB1

# Tag the current state (useful for rollback points)
echo "lb tag v0.1
EXIT" | sql -s system/OracleLocal26ai@localhost:1521/FREEPDB1
```

**How Liquibase tracks history:**
After the first `lb update`, Oracle creates a `DATABASECHANGELOG` table in your schema. Each row is one applied changeset. Run `lb update` again and it will skip everything already in that table — only new changesets run.

```sql
-- Inspect what has run
SELECT id, author, filename, dateexecuted FROM databasechangelog ORDER BY dateexecuted;
```

---

## Changeset Rules

### Stateful changes (run once, never modify)
Tables, indexes, sequences, constraints. Lives in `releases/YYYY.MM/`:

```sql
--liquibase formatted sql

-- changeset author:unique-id
-- comment: WHY this change is needed
CREATE TABLE my_table (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(100) NOT NULL
);

-- rollback DROP TABLE my_table;
```

**Rule:** Once a changeset is committed and applied anywhere, never edit it. Add a new changeset instead.

### Stateless changes (repeatable, idempotent)
Packages, procedures, functions, views, triggers. Lives in `packages/`, `views/` etc. with `runOnChange: true` — re-applied every time the file changes.

```sql
--liquibase formatted sql

-- changeset author:pkg-customer-body runOnChange:true
-- comment: Customer package body
CREATE OR REPLACE PACKAGE BODY pkg_customer AS
    ...
END pkg_customer;
/
```

---

## Why Migration-Based (Not State-Based)?

**State-based tools** (like Flyway diff mode or some ORM tools) compute the difference between "desired state" and "current state" and generate SQL automatically. Simple for development, dangerous in production: they can roll back hotfixes when syncing to a new baseline.

**Migration-based** (Liquibase default): every change is an explicit, ordered, auditable script. You know exactly what ran, when, and in which environment. Rollbacks are deliberate, not automatic.

For Oracle with long-lived production databases, migration-based is the industry standard.

---

## Useful Commands

```bash
# Stop Oracle (data persists in volume)
docker compose down

# Stop and delete all data (clean slate)
docker compose down -v

# Open SQL*Plus inside the container
docker exec -it oracle-free sqlplus system/OracleLocal26ai@FREEPDB1

# Check container health
docker inspect oracle-free --format "{{.State.Health.Status}}"

# Diff current DB state vs changelog (drift detection)
echo "lb diff
EXIT" | sql -s system/OracleLocal26ai@localhost:1521/FREEPDB1
```

---

## Architecture Context

This Oracle setup is one layer of the full reference stack. See the [architecture overview](../../README.md) for how Oracle, ORDS, and the Python API fit together.

The Python API is the **only** application interface to this database. See [ADR-002](../../docs/adr/002-api-only-db-access.md).
