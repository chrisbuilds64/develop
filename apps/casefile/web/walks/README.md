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

`gate-shot.mjs` photographs the gate (ADR-024) in sample worlds at 1440 light/dark and 390 and measures what the design rules
demand (targets ≥ 24 px, keyboard stops inside the viewport, no horizontal scroll). It takes `<base> <outdir> <workspace>:<case>:<person> …`;
the stage comes from `control/demo/stage.py <worlds> <trees> <port> schadenakte-muster=claims pressroom-muster=pressroom …`.

`stack-shot.mjs` photographs the stack (ADR-024, step 2): a workspace's start page at 1440 light/dark and 390, plus named cases as
the gate, and measures the same rules plus one more — at most one surface framed in `--your-move`, and only the piece that waits
for the viewer. It takes `<base> <outdir> <workspace>:<person>[:<case>,<case>] …`; the stage is the same as for `gate-shot.mjs`.
Restart the stage after a rebuild: it serves the asset names it read at start.
