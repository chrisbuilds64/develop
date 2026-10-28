"""Keep only the statements of a generated changeset that carry the real change.

SQLcl's `project stage` compares snapshots. When the target was built by a deploy, a column default is stored as it was
written (`sysdate`), the baseline harvested from PROD has `SYSDATE`, and stage turns that spelling into `modify … default`
statements and re-adds an existing check constraint (its DROP left commented out for review). Those statements change
nothing or fail. This keeps every statement except: `modify (… default …)`, `add constraint` and commented-out blocks.

    python3 trim_changeset.py <changeset.sql>     # rewrites the file, prints what it dropped
"""
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
head, _, body = text.partition("\n\n")
parts = [s.strip() for s in re.split(r"\n/\n", body) if s.strip()]
keep, dropped = [], []
for s in parts:
    plain = s.strip()
    if plain.startswith("/*") or re.search(r"\bmodify\s*\(.*\bdefault\b", plain, re.S | re.I) or re.search(r"\badd constraint\b", plain, re.I):
        dropped.append(plain.splitlines()[0][:90])
    elif plain.startswith("--") and "sqlcl_snapshot" in plain:
        keep.append(plain)
    else:
        keep.append(plain if plain.endswith("/") else plain + "\n/")
p.write_text(head + "\n\n" + "\n\n".join(keep) + "\n", encoding="utf-8")
for d in dropped:
    print(f"dropped: {d}")
