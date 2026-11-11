# Walks

Playwright scripts that click through the demo like a visitor and take screenshots: the claims path, the e-report path, the
round trip between claim and e-report, the three views, the reader, the language switch, dark mode, the patterns view.
Each takes `<base> <outdir>`; against a deployment under a path prefix, set `BASE_PATH` (for example `/demo`).

```
cd apps/casefile/web && npm install            # playwright is a devDependency
npx playwright install chromium                # once per machine
node walks/loop-shot.mjs http://127.0.0.1:8410 /tmp/walk-out
BASE_PATH=/demo node walks/loop-shot.mjs https://your-host /tmp/walk-out
```

Every script prints what it saw and ends with `ISSUES (n)`: console errors, page errors and HTTP errors ≥ 400 it met on the way.

## Walks in CI

A walk that proves a requirement line is a check: CI plays it on every pull request that needs it. Declare it in
`sandbox/walks.json` — `id`, `script`, the `workspaces` it plays (passed to the script after `<base> <outdir>`, in this
order) and the lines it `proves`. Nothing else registers it.

Which checks a pull request needs is computed from its diff (`sandbox/sandbox.py ids BASE HEAD`, rules in `touched`): a
change to an application's configuration or sample world plays the flows and walks of the workspaces that use it; a change
to the walk's own script plays that walk; a change to the core, the surface or the sandbox plays every check; docs, unit
tests, the cockpit shell, deploy tooling and guards play none. Try the rules with `sandbox.py ids --files <path> …`.
