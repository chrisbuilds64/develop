---
version: 1
slug: "cockpit-templates-desk-html"
primary_target: "cockpit/templates/desk.html"
related_targets: ["cockpit/templates/piece.html"]
---

# Surface brief — the desk (`/m/pipeline`, view desk) and the piece page

Scope: the creator's start page and one piece's page. Mode: Operate. Established world inherited
from `cockpit.css` (blue-black ground, slate surfaces, blue accent, Inter, 12px radii, derived
light mode). The workshop view, the tools and the reader's contracts stay untouched.

Audience and job: a creator who thinks in pieces and in what happens next; a prospect watching a
five-minute demo who must recognise a case flow in it. Task: see what waits for me, press the one
button, read a draft, answer a note, approve, pick a date. Constraints: words only, no codes; one
button per piece; every file reachable; works at 390px; German demo.

seed: 47892339ea7c9507e99787762e82b1e4 (surface, operate). Grounded list (ranked): focus deck ·
journey tracks · pipeline strip as tabs · dossier stack · day sheet · calendar-led · wall of
covers. Dealt 7, 5, 6; 7 leads. Unattended run: the lead is locked and fused with the day sheet
(5); the calendar (6) fails product clarity because a date exists only at the fifth step.
Challengers declined: the streaming title wall (closest to the lead, kept as the shelf idea only;
its hover-reveal would hide the button, which the mode forbids); the others are costumes.

## Direction contract

THESIS: A piece is a cover on a shelf, and the shelf you see first is the one that waits for you.
The page refuses the kanban of stage columns and the grouped list of same-size cards: no stage
is named, no column is scanned; the person reads one sentence and one button per piece.

OWN-WORLD: Inherited tokens. Covers (`cover_svg`, already deterministic per piece) carry the
only colour besides the accent; everything else is ink on slate. One sans. State is a short
sentence in the person's words, never a badge with a code. The one button is filled accent;
every secondary action is quiet text.

FIRST VIEWPORT: Top: the product name and the day in words ("Montag, 20. Oktober"), the switch
to the workshop, and the one intake button. Then the lead line: "Drei Stücke warten auf dich."
Then the first shelf, "Wartet auf dich": covers in a row, each with title, state sentence, a
six-dot path showing where the piece is on its way, and its button. Shelves below: In Arbeit,
Bei <partner>, Geplant, Ideen; "Draußen" is a count with a link, not a shelf.

SIGNATURE MOVE: The six-dot path. Every card and the piece head carry the same six steps
(Idee · Ausarbeitung · Durchsicht · Bild · Termin · Draußen); the current one is lit in the
accent, the done ones filled, the rest hollow. On the piece page it grows into a labelled
stepper whose current step holds the button. The prospect reads the process from the dots
before reading a word.

VISITOR PATH: desk → one button → piece page (head with path and button; draft readable in
the page; notes as a conversation with Antworten / Erledigt / Freigeben; helpers as a quiet
row with their last run) → back to the desk, where the shelf has changed.

CROSS-SURFACE REACH: The path and the state sentence are the only things the claims variant
changes through `vocabulary.json`; the shelf, the button and the page are the same. Light mode
derives from the same tokens.

HONEST RISK: Covers are generated art; with many pieces a shelf could read as decoration. Kept
in check by the state sentence and button being larger than the cover, and by a shelf showing
at most six covers before "alle zeigen".
