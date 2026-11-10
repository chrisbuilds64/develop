# ADR-032: What a Workspace Is

**Status:** Accepted (2026-11-09, product owner). Supersedes ADR-018 decisions 2 to 4.
**Date:** 2026-11-09

---

## Context

ADR-018 defined a workspace as "one tree of folders under one application, with an owner or shared, with members". The
code followed it: one `application` and one root per registry entry, one casefile app per `/w/<id>/`, one queue and one
`pressroom` link per run, one team folder per pressroom-env space. Privacy became workspace membership.

The product owner meant something else from the start (2026-11-09): a workspace is a configured set of **access points to
data** — folders, databases, mailboxes — in which **several applications** run and **several people** work. Applications
are abstract; what they work on depends on where they are pointed. The same application can run more than once in one
workspace, for training and for production. And the model has to carry a tenant later: a tenant has a workspace set up,
configures its data points, registers its users and its agent instances from the available signatures.

The point is not to reinvent anything. The point is to show that configuration and abstraction make a flexible system:
the terms below are those of Slack, Notion or any multi-tenant platform, applied to casefile.

The seed is already there: ADR-018 planned the entry to grow into "a list of components … the application declares what
it needs"; ADR-020 called the workspace "a list of sources and sinks that applications bind to". A check of the code and
all records (2026-11-09) found where the old notion is assumed; the ranked list is under Consequences.

## Decision

1. **Eight terms, one meaning each** (the connector added 2026-11-10, see below).
   - **Tenant** — owns workspaces, people, agent instances, connectors and billing. Today there is one, ChrisBuilds64.
   - **Workspace** — a set of data points, the application instances running on them, and members.
   - **Connector** — a technical access the tenant sets up once: a Nextcloud server, a directory on a host, a database
     server, a mail server, a repository host. It carries the kind, the address per stage and the credentials. It
     holds no data of its own and grants no rights to anybody.
   - **Data point** — a named place reached through one connector: a team folder, a directory, a schema, a mailbox,
     a repository. It belongs to one workspace and carries who may read or write it.
   - **Application** — configuration only: stages, words, documents, roles, skills (ADR-015). It holds no data and is
     never stored in data.
   - **Application instance** — an application running in a workspace under a name of its own, with its slots bound to
     data points and with house rules that override the application's defaults.
   - **Member** — a person or an agent instance in a workspace, with roles per application instance.
   - **Stage** — a version of the code (ENTW, TEST, PROD, ADR-017). Orthogonal to all of the above.
2. **Rights live on the data point, enforced where the data lives.** Membership lets a person into a workspace; access
   to a data point decides what they see, enforced by the store itself (Nextcloud folder rights, database grants), never
   only by a filter in the surface. Roles in an application instance decide what a member may *do* there.
3. **An application declares slots, an instance binds them.** A slot names what the application needs ("cases",
   "inbox", "documents"); the instance binds each slot to one or more data points. Several data points in one slot are
   read together; each member sees those they may read. The binding, the instance's name and its house rules live in the
   workspace's configuration — not in the data tree.
4. **Several instances of one application per workspace.** "PressRoom" and "PressRoom training" are two instances of
   one application over different data points. The `-muster` workspaces of today are such instances.
5. **Hand-off goes from instance to instance** through their bindings inside a workspace. Across workspaces it needs a
   connection the tenant sets up. `targets.json` in a data tree goes away.
6. **The tenant registers agent instances** from the available signatures; an agent instance is a member of workspaces
   like a person. **The tenant pays** for every run, of people and agent instances alike.
7. **Stages are separate worlds.** ENTW, TEST and PROD each hold their own copy of every data point (ADR-017). As an
   exception, a data point may be shared by a stage with another one — for example a Nextcloud folder that ENTW reads
   as well — but only declared explicitly on that data point, never by default. A **sandbox** is a copy of a workspace
   within a stage: its data points are copied, its application instances stay as they are.
8. **The model carries the tenant from now on**, with one fixed value. No multi-tenant feature is built yet; no new code
   may assume there is only one.
9. **The word is used for this alone.** The runner's per-run home directory and pressroom-env's "space" get other names.

## Consequences

Ranked by weight, from the check of 2026-11-09 (full list: `control/planning/2026-11-09_workspace-bestandspruefung.md`,
private):

1. The 1:1 link workspace–application runs through the registry format, the `/w/<id>/` mount, `create()`, and
   pressroom-env's spaces. It becomes workspace → instances → bindings.
2. The casefile core knows one root and one configuration (`Settings`), and a data tree can override the application
   (`people.json`, `run-policy.json`, `_ablauf/`). The core has to take a binding instead, and application settings
   leave the data.
3. Privacy as membership (`visible_to`, the `/w/` gate) and ADR-031 decision 2 give way to rights on data points.
4. The runner assumes one data root per run (queue, `pressroom` link, `PRESSROOM_WORKSPACE`). A run gets its instance
   and that instance's bindings.
5. Hand-off via `targets.json` (ADR-022/023) becomes instance-to-instance.
6. There is no tenant layer yet: global user roles, global accounts, one agent catalogue per stage.
7. Agents and billing hang on the person (ADR-020, `bill_to`).
8. A mailbox is a file in the tree plus a person's credentials; it becomes a data point.
9. Per-workspace settings in the drafts (ADR-029 protocols, ADR-030 delivery) move to the instance.

The change is large and goes in steps, each a Shipyard case, each leaving production running. Order and size are a
separate plan; nothing in this record is built by accepting it.

## Decided with the acceptance (2026-11-09)

- **Billing:** the tenant pays (decision 6).
- **Set-up:** the tenant's administrator sets up data points, application instances and members.
- **Order:** the worklist (ADR-031) is the first application built on this model; the rest follows case by case.

## Amended 2026-11-10: connectors

Decision 1 had the data point carry its location, its credentials and its rights at once. The product owner separates
them (2026-11-10): **connectors** are a pool of the tenant; a workspace takes **data points** from that pool; the
application instances of the workspace bind their slots to those data points.

    tenant ── connectors (kind, address per stage, credentials)
                 │ one connector, many data points
    workspace ── data points (place on a connector, readers, writers)
                 │ bound by slots
                 └─ application instances (application, name, house rules, mode)

- Credentials live once, on the connector; a data point names its connector and a place on it.
- Rights stay on the data point (decision 2) and are enforced through the connector where it can (Nextcloud folder
  rights, database grants); where it cannot (a plain directory), by the scoped store alone.
- Stages (decision 7) are an address per stage on the connector, so a data point needs no copy of its own description
  per stage.
- The words are English in configuration and code: `connector`, `data point` (`data_points`), `workspace`,
  `application`, `instance`, `slot`, `binding`, `member`, `tenant`.

**Today's registry read in these terms (PROD, 2026-11-10).** Every entry of `workspaces.json` is an application
instance with exactly one data point; the shell's "Casefile" entry lists all of them. Two entries over the same
application differ only in their data point: `pressroom` (live, a Nextcloud team folder) and `pressroom-muster`
(replay, a directory seeded from `worlds/pressroom-muster`). The registry also lists "PressRoom · Muster" as an
application of its own, although it points at the same configuration — the sample is in the wrong place there; it is a
data point with a seed, not an application. The steps from this shape to the one above are planned in
`control/planning/2026-11-10_workspaces-connectors-case-tree.md` (private).

## Alternatives considered

- **Keep ADR-018 and add a second application by a second workspace.** What we do today; it multiplies workspaces,
  copies configuration into data and makes privacy a matter of where an application runs.
- **Privacy by filter in the surface.** Rejected in ADR-031 already: the files stay readable outside the surface.
