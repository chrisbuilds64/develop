# The database that cannot rebuild itself — demo world (DOAG 2026)

An order-management schema (`SDLC_APP`, the OV teaching schema from `../test-schema/`) as it is often found in
production: installed in 2016, patched by script ever since, with an APEX app on top. The demo shows the way out:
harvest the database into Git, compare the old script folder against it, rebuild a database from the repository
alone and prove it with an empty diff.

Runs on the database host against the three PDBs from `infra/ansible/oracle.yml` (ENTW, TEST, PROD). ENTW is not
touched; PROD and TEST are demo databases.

## Layout

| Path | What it is |
|---|---|
| `altbestand/` | the legacy as exported from CVS: `install/` (2016), `patches/` P001–P004, `apex/f106.sql` (monolith export) |
| `world/` | stage setup only, never part of the legacy: what happened in PROD without a file (hotfix, index), movement data |
| `bin/doag` | the pipeline: `reset`, `scripts`, `harvest`, `compare`, `rebuild` |

## The three planted truths

1. `world/prod_hotfix_2024-11.sql` — a package hotfix applied directly in PROD. No file in the legacy has it.
2. `altbestand/patches/P003_2023-05_kunden_uid.sql` — in the folder, never applied to PROD.
3. `world/prod_index_2022.sql` — an index that exists only in the database.

## Run

```
doag reset          # PROD as it really is, TEST behind, a fresh repository holding the CVS export
doag harvest PROD   # SQLcl project export on a branch, stage, merge, release 1.0
doag scripts TEST   # the classic way: install + every patch in order
doag compare TEST   # → four files differ: the three truths
doag rebuild TEST   # drop the schema, deploy release 1.0 from the repository (~15 s)
doag compare TEST   # → no difference: TEST is the baseline
```

Needs SQLcl (a copy in `$DOAG/sqlcl`), git, the `oracle-free` container and `$DOAG/.env` with `APP_PW`.
The password never lives in this repository.

## Talk 2: a change through the gates

```
doag adopt PROD       # PROD was built by scripts: record release 1.0 as present (changelog-sync), execute nothing
doag entw             # ENTW gets the baseline beside the workshop's apps
doag change           # a developer adds liefertermin in ENTW (column, package, function)
doag capture          # branch, export ENTW, changesets plus the backfill as a custom changeset
doag impact PROD      # read-only questions to PROD, each printed with its query
doag prepare          # trim the generated changeset, merge, release 1.1, artifact, rollback
doag deploy TEST      # 5 changesets run, 22 skipped; then doag compare TEST → no difference
doag deploy PROD      # refused: no guaranteed restore point younger than two hours
doag restore-point PROD && doag deploy PROD
```

The restore point needs a Fast Recovery Area on the CDB (`db_recovery_file_dest`), which the demo database does not
have yet.

## What we found on the way (SQLcl 25.1, APEX 26.1, Oracle AI Database 26ai Free)

- `project export` writes APEX applications as **APEXLang** (`apex_apps/f106/**/*.apx`) when the database runs
  APEX 26.1. Readable, diffable, one file per page.
- `project stage` does not turn those `.apx` files into changesets, and `APEX_APPLICATION_INSTALL.install` does not
  accept them (neither as a file list nor as a zip). The repository therefore carries the app twice: APEXLang to read
  and compare, `apex/f106.sql` to install.
- `project stage` refuses to run on `main` (protected branch). Harvest happens on a branch and is merged.
- SQLcl reads **stdin** as Latin-1 regardless of `LANG` and `file.encoding`; scripts passed with `@file` are read as
  UTF-8. `bin/doag` therefore always writes a script file.
- After a deploy, SQLcl's `-- sqlcl_snapshot` line records a column default as it was spelled in the DDL
  (`sysdate` instead of `SYSDATE`). The DDL itself is identical; `compare` ignores the snapshot line.
- Liquibase leaves its tracking tables (`DATABASECHANGELOG*`) in the target schema; the project export ignores them.
- After a deploy, `project stage` reads the spelling difference `SYSDATE`/`sysdate` as a change: it generates
  `modify (… default sysdate)` statements that change nothing and re-adds an existing check constraint, with the DROP
  before it commented out for review. Deployed as generated, that changeset fails (ORA-02264). `capture` leaves out files
  that differ only in the snapshot line; `prepare` keeps only the statements that carry the change
  (`bin/trim_changeset.py`). The raw changeset stays as evidence.
- A database built by scripts has no Liquibase history. Before the first deploy there, `lb changelog-sync` records the
  baseline release as present without executing it (`doag adopt`).
