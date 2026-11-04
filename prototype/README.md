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
- **Guides** (top right on Home): short tours through the main flows, and a Videos list with the nine tutorial chapters.
- Light and dark mode, English and German (profile menu, bottom left).

## Shortcuts

⌘K search · ⏎ confirm · J next · K previous · A archive · ⌘J ask the AI · ? all shortcuts · Esc back.

## Backend needs

What the design needs from the backend is listed in the Claude Doc "Requests for Chris: design hand-back".

## Tutorial videos

The player expects the files in `prototype/videos/` (`en-01.mp4` … `de-09.mp4`, posters `*.jpg`, `chapters.json`). They are not in git because of their size (about 157 MB); they come separately as a zip. Without them the prototype works, only the videos don't play. See request #10 in "Requests for Chris".
