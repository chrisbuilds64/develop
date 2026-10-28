# pressroom-env — the PressRoom in stages

ENTW, TEST and PROD of the PressRoom on one server, told apart by the URL path: `/` is production,
`/test/` and `/entw/` are stages. Each stage has its own Nextcloud team folder, its own WebDAV mount,
its own cockpit and its own headless skill runner. The stages are described in one file, `envs.toml`,
and this tool makes the server match it.

```
pressroom-env status                   every stage: units, port, path, team folder
pressroom-env create  test             team folder, mount, code, cockpit, runner — and the first clone
pressroom-env clone   test             fresh test data: production copied onto the stage
pressroom-env deploy  test --ref v0.11 develop at a reference, cockpit reinstalled, units restarted
pressroom-env nginx                    the location blocks for the prefixed stages
pressroom-env render  test             print what would be installed, install nothing
```

Runs as root on the server. Nextcloud's `occ` runs as the site user, `git` and `pip` as the runner.
Standard library only; Python 3.11+.

## Three ideas

**A stage is configuration.** Team folder, mount, port, prefix and code reference live in `envs.toml`
([example](envs.example.toml)). The tool renders the cockpit configuration, the systemd units, the
runner's workspace and the nginx locations from it. Nothing is edited by hand twice.

**What we use and show lives in production.** The sample worlds and the live demos (Gatehouse, inbox, the DOAG
files) are set up on the showcase stage only — by default the one that is no clone target (`showcase` in `envs.toml`).
ENTW and TEST carry the PressRoom alone.

**Test data is production, cloned.** `clone` copies the production team folder onto the stage on the
disk (`rsync`), leaves the run queue behind, writes `flow/environment.json` as the marker, and tells
Nextcloud to rescan. A developer never works against an invented pipeline. Nothing flows back: a
clone target is declared (`clone_from`), production never is.

**Code is staged, rules are not.** Each stage checks out `develop` at its own reference and installs
the cockpit from it, so ENTW can run tomorrow's cockpit while PROD runs today's. Canon and skills
(`canon/`, `control/`) are shared and pulled by the runner before every run — they are rules and
state, the same for everyone, and always current.

## What a stage looks like on the disk

```
/home/runner/envs/<stage>/
  develop/                    checkout at the stage's ref
  cockpit/                    cockpit.toml · cockpit-audit.jsonl · plugins/ · .venv/
  home/                       HOME of the stage's runner
    .claude.json              trust for the workspace
    ChrisBuilds64/            the workspace a headless session starts in
      CLAUDE.md               slim runner instructions, stage named
      .claude/settings.json   permissions (the context comes as system prompt, see below)
      .claude/skills, agents  → ../control/claude/…
      canon, control          → /home/runner/ChrisBuilds64/… (shared)
      develop                 → ../../develop
      pressroom               → /srv/pressroom-<stage>  (davfs2 mount)
      tmp/
```

Why a HOME per stage: the skills address the pipeline as `~/ChrisBuilds64/pressroom/flow`. With its own
HOME each runner resolves that to its own stage, and the skills stay the files the person uses at the
keyboard.

## Units

`srv-pressroom\x2d<stage>.mount`, `pressroom-cockpit-<stage>.service`, `pressroom-runner-<stage>.service`.
`systemctl status 'pressroom-*'` shows everything. The root stage replaces the single-stage units of
2026-10-13 (`pressroom-runner.service`, `pressroom-cockpit.service`) when it is created.

## nginx

The vhost keeps `location /` for production and includes the generated snippet once:

```
include /etc/nginx/pressroom-envs.conf;
```

Each prefixed stage is one `location /test/ { proxy_pass http://127.0.0.1:8201/; … }` — nginx strips the
prefix, and uvicorn puts it back as `root_path` (`base_path = "/test"` in the cockpit's configuration).
Uvicorn prepends `root_path` to every path it receives, so the proxy must not send the prefix twice.

## How a run from the button knows what a keyboard session knows

The runner hands the order to the session as environment (`PRESSROOM_ENV`, `PRESSROOM_SKILL`,
`PRESSROOM_CONTAINER`, `PRESSROOM_ORDERED_BY`, `PRESSROOM_AGENT`), runs the context script
(`control/claude/hooks/runner-context.py --plain`), and gives the session the result as an appended
system prompt file. The script reads `control/shared-context/context-manifest.json` — the list of files
an instance knows before it works, curated in one place — and inlines them: the same files
`/session-start` reads at the keyboard, chosen by instance and by the skill's domain. A SessionStart
hook cannot carry this: Claude Code keeps hook output above a few kilobytes out of the context
(observed 2026-10-24, 110 KB saved to a file with a 2 KB preview), so the system prompt is the path.
