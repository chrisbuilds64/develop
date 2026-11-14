# REQ-008 — A static site as a deploy target

**Status:** proposed 2026-11-14. Decision record: ADR-036.

**Scope:** uploading a folder of static files to the place that serves them, as three steps a person or a run can
take: plan, apply an approved plan, verify. The first target kinds are a directory and an FTP account over TLS. Not in
scope: the Casefile application around it (stages, gates, a preview stage), deleting on the server, building the site.

**Evidence** means a test in `apps/casefile/tests/test_site_target.py`, unless the row names another.

## Requirements

### The description

| # | Requirement | Evidence |
|---|---|---|
| ST-01 | A site is described by one file kept with the site: source folder, target, public address, what is excluded, what is protected, what must not be served. Nothing about a particular site is in this repository. | `test_a_description_with_an_unknown_key_or_without_a_source_is_refused` |
| ST-02 | Credentials are never in the description. They come from the environment of a run or from a file outside every repository that the description names. | `test_credentials_come_from_the_environment_or_a_named_file_never_from_the_description` |

### The plan

| # | Requirement | Evidence |
|---|---|---|
| ST-03 | The plan names every file as new, changed or the same, and lists what only the server has and what is protected. Making a plan changes nothing. | `test_the_plan_sorts_every_file_and_touches_nothing` |
| ST-04 | Excluded and protected files never leave the source. | `test_excluded_and_protected_files_never_leave_the_source` |
| ST-05 | A plan has an id that names what would be written and onto what. | `test_apply_refuses_when_the_source_changed_after_the_plan_was_read` |

### Apply

| # | Requirement | Evidence |
|---|---|---|
| ST-06 | Apply uploads the plan whose id it is given and no other. If the source or the server changed since the plan was read, nothing is uploaded. | `test_apply_refuses_when_the_source_changed_after_the_plan_was_read`, `test_apply_refuses_when_the_server_changed_after_the_plan_was_read` |
| ST-07 | Nothing is deleted on the server. Protected paths are never written. | `test_apply_uploads_the_approved_plan_and_keeps_what_it_replaces` |
| ST-08 | Every file that is replaced is saved first, under the id of the plan: the way back. | same |
| ST-09 | A file arrives whole: uploaded under a temporary name, then renamed. Files and folders get the modes the description names; where the target cannot set them, the result says so. | same |

### Verify

| # | Requirement | Evidence |
|---|---|---|
| ST-10 | Verify fetches every file of the source from the public address and compares the bytes. Files the server executes or withholds are named as not compared. | `test_verify_compares_what_is_served_with_the_source` |
| ST-14 | Verify pauses between two requests, so a hoster's flood protection does not lock the address out. | by hand: found on the first real run, 2026-11-14 |
| ST-11 | Verify fails when a path that must not be served is served. | `test_verify_fails_when_a_file_that_must_stay_private_is_served` |

### Use

| # | Requirement | Evidence |
|---|---|---|
| ST-12 | Each step is one command and can write its result as a report file, to be laid into a case. | `test_the_command_line_plans_applies_and_writes_a_report` |
| ST-13 | The FTP target works against a hoster's account over explicit TLS. | by hand: first real upload 2026-11-14, 30 files, verified against the live site |
