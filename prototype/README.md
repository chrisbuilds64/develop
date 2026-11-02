# Casefile prototype (design reference)

A clickable prototype of the reimagined Casefile design. It is the reference for how the app should look and behave. It is not connected to the backend, and all data in it is fictional.

## Open it

```
cd prototype
python3 -m http.server 8300
```

Then open http://localhost:8300.

## What to look at

- **Home:** what needs you today, grouped by urgency.
- **A case (open any row):** AI summary, facts, quotes from the mail, the AI suggestion and the actions.
- **Board and Table views** in each workspace.
- **Admin:** AI team, Rulebook, Flagged, Setup.
- **Guides** (top right on Home): short tours through the main flows.
- Light and dark mode, English and German (profile menu, bottom left).

## Shortcuts

⌘K search · ⏎ confirm · J next · K previous · A archive · ⌘J ask the AI · ? all shortcuts · Esc back.

## Backend needs

What the design needs from the backend is listed in the Claude Doc "Requests for Chris: design hand-back".
