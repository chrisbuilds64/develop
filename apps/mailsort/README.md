# mailsort

Pre-sorts incoming mail from several IMAP mailboxes into folders of one target mailbox. Deterministic rules
first, AI only for what no rule decides, nothing ever deleted. Standard library only, Python 3.11+.

**Status:** exploration. Inventory, rule bootstrap and a dry-run preview exist; nothing moves mail yet.

## Configuration (never in this repo)

`~/.config/mailsort/accounts.toml`:

```toml
target = "me@example.com"            # the account that holds the target folders
secrets_dir = "~/.secrets/mailsort"  # one file per account, named by address, containing only the password (mode 400)

[[account]]
address = "me@example.com"
host = "imap.example.com"
```

`~/.config/mailsort/rules.toml` is the rulebook: per target folder its kind, sender domains, subject keywords and a
hint for the AI. `mailsort.bootstrap` drafts it from an inventory.

## Commands

All read-only. Output goes to a private directory, never a repository.

```
python -m mailsort.inventory --out <dir>                    # folders, counts, headers of every mailbox
python -m mailsort.bootstrap --inventory <dir> --root <p>   # draft rules.toml from the existing folders under <p>
python -m mailsort.preview --inventory <dir>                # where the inbox backlog would go
```

Mailboxes are opened read-only and headers fetched with `BODY.PEEK`, so no flag changes.

The decision itself lives in the casefile core (`apps/casefile/casefile/domain/sorting.py`, ADR-023): the same rules
sort a casefile inbox before its helper reads anything. `mailsort.rules` maps the folders of `rules.toml` onto it.
