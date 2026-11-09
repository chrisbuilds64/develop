# casefile in one page

**casefile is a worklist whose items carry documents and are checked at gates.**

Everything else is configuration. The worklist is casefile with nothing added, so it is the place to learn it.

## Every concept, on a to-do

| Concept | In the worklist | What it is in general |
|---|---|---|
| **Case** | one to-do, `SYS-147` | a folder with a `meta.json` and a thread (`review.md`); the folders are the truth |
| **Stage** | Backlog, Next, Doing, Waiting, Done | a folder the case stands in; moving the case is renaming the folder |
| **Whose move** | the assignee | one function over the case and its stage; the surface, agents and the command line ask the same one |
| **Step** | "Start", "Done", "Change" | one move, whole or not at all, journaled; the same step twice changes nothing |
| **Value list** | area, priority, origin | the fixed values a case may carry, with words and colours |
| **Field** | assignee, due date | a declared value a person may change; the thread names old → new |
| **Document** | a sketch, a draft attached to the to-do | any file in the case folder, versioned by name (`draft.v2.md`) |
| **Gate** | none — every member moves every item | a move only a role may make, with what must be present first, four eyes if asked |
| **Dependency** | "waits for SYS-136" | a case waits for others, also in other applications; released when they close, never moved by itself |
| **Hand-off** | share to the team, delegate to a person | a case moves to another data point, or opens a case somewhere else with a link back |
| **Data point** | my private folder, the team's folder | where the cases lie and who may read and write them; the protection is the store's, not the screen's |
| **Application instance** | "Worklist" in the team workspace | an application (pure configuration) bound to data points; one application can run many times |
| **Workspace** | ChrisBuilds64 | data points, the application instances on them, and the people and agents who work there |

## What the other applications add

| Application | Adds words | Adds required documents | Adds gates |
|---|---|---|---|
| **PressRoom** (content) | idea, draft, review, published | the text before review, the images before release | the author's text gate, the image gate |
| **Shipyard** (software changes) | task, pull request, release | task, pull request, check run, release record | the product owner merges and accepts each stage; never the author |
| **Claims file** (insurance) | claim, assessment, payout | the claim, the invoice, the assessment | four eyes above an amount; no payout without an invoice |
| **Inbox** (mail) | mail, rule, hand-off | the mail itself | a person confirms the rule before a case opens elsewhere |

Each is the worklist plus those three things — written in configuration files, not in code. That is the claim of the
system, and the worklist is where it can be checked: if something a domain needs cannot be said in words, required
documents and gates, the core is missing a concept, and the concept goes into the core for every domain at once.

*Records: ADR-031 (the worklist), ADR-032 (what a workspace is), ADR-015 (domains as configuration), ADR-013 (files
are the truth). The demo world "Worklist" shows every row above on invented to-dos.*
