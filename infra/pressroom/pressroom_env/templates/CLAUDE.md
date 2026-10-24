# Runner workspace — stage {{label}} ({{env}})

This is the headless skill runner of the ChrisBuilds64 PressRoom, stage **{{label}}**. A session here is
started by `runner.py` with one order: run one skill on one container. Do that, report in five lines, stop.

- **Stage:** `{{env}}`. Everything you read and write under `~/ChrisBuilds64/pressroom/` belongs to this
  stage only. A clone of production is still a clone: nothing flows back to another stage.
- **PressRoom:** `~/ChrisBuilds64/pressroom/flow/` (a WebDAV mount of the stage's Nextcloud team folder,
  `{{mount}}`). Stage folders are the status. Write only inside the ordered container, or where the skill says.
- **Canon:** `~/ChrisBuilds64/canon/` — binding editorial and brand rules; the skills load what they need.
- **Context:** the runner has put the operating context in front of you as part of your system prompt (RUN
  CONTEXT) — signature, governance, project state, the latest session log, current intent. Work from it as the
  person at the keyboard would; do not re-read those files.
- **Skills and agents:** `.claude/skills/`, `.claude/agents/` (fact-checker, boundaries-reviewer).
- **Temporary files:** `~/ChrisBuilds64/tmp/`, never /tmp.
- **Language:** public content English; internal notes, review entries and your closing report German.
- **Versions:** never overwrite a deliverable — a revision is `<name>.v<N>.<ext>` (pressroom/CONTRIBUTING.md, rule 1).
- **When the skill would ask a question:** do not guess. Write one review entry addressed to the person who
  ordered the run (`For`), say what you need, and stop. The container stays where it is.
- No git here. No session-start, no session-end, no memory. Nothing outside this workspace.
