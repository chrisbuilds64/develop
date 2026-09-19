# Feldorakel — frozen 2026-09-19

Farmers' weather lore for the DACH region: a set of traditional rules (`rules.json`,
`rules_en.json`) read against a forecast, with the interpretation written by a language model.
Bilingual DE/EN, FastAPI, one page, one endpoint.

**This app is no longer running.** It was stopped on 2026-09-19. The code stays here; nothing
about it is broken.

## Why it was stopped

The app was the only consumer of an Anthropic API key on the production server. During a key
rotation we looked at what that key was actually doing, and the answer was: almost nothing.

| Period | Model calls (`POST /forecast`, HTTP 200) |
|---|---|
| 2026-07 (from the 20th, when logs begin) | 1 |
| 2026-08 | 0 |
| 2026-09 | 0 |

The landing page was still being opened by 120–190 distinct addresses a month, but nobody
submitted the form. Everything else in the access log was scanner traffic (`/.env`, `wp-json`,
`eval-stdin.php`). A public endpoint with model access that nobody uses is attack surface and a
running cost, not a product.

## What was done

- Both Caddy routes removed (`feldorakel.chrisbuilds64.com`, `feldorakel.chrisbuilds64.dev`)
- Container `plowcast` stopped and removed
- `/opt/feldorakel/.env.local` deleted — the server no longer holds an Anthropic key
- DNS records still point at the host; the names now fail the TLS handshake

The rendered landing page was archived outside this repository before shutdown.

## Running it again

Nothing here needs changing. Build the image, provide `ANTHROPIC_API_KEY` in `.env.local`, start
the container on the `caddy-net` network and add the host block back to the Caddyfile.

Two things to know first:

1. **The dependencies are from 2026-07-20** (19 CVEs patched then, `starlette` 1.x). Run
   `pip-audit -r requirements.txt` before exposing it again.
2. **`caddy reload` does not work on that server.** The admin API on `localhost:2019` is
   disabled, so the command adapts the file, reports success, and leaves the running instance
   untouched. Use `docker compose restart caddy` and expect a few seconds of downtime for the
   API that shares the proxy.
