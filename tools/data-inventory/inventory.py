"""Data inventory crawler — read-only scan of a directory tree.

Answers the four questions a data inventory has to answer on day one:
how much is there, how much of it is duplicated, how much has not been
touched in years, and who owns it.

This tool never deletes, never moves and never writes into the scanned
tree. Its output is always a proposal for a human to decide on.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Age buckets in years. The last bucket is open-ended.
AGE_BUCKETS = (1, 3, 5, 10)

# Read files in chunks so a multi-GB file does not land in memory.
HASH_CHUNK_BYTES = 1024 * 1024


@dataclass
class FileRecord:
    path: Path
    size: int
    modified: datetime
    owner: str


@dataclass
class ScanResult:
    files: list[FileRecord]
    unreadable: list[tuple[Path, str]]
    skipped_symlinks: int


def owner_name(uid: int) -> str:
    """Resolve a numeric uid to a login name, falling back to the number.

    Orphaned files whose owner no longer exists are exactly the ownership
    gaps the inventory is looking for, so an unresolvable uid is data, not
    an error.
    """
    try:
        import pwd

        return pwd.getpwuid(uid).pw_name
    except (ImportError, KeyError):
        return f"uid:{uid}"


def scan(root: Path) -> ScanResult:
    files: list[FileRecord] = []
    unreadable: list[tuple[Path, str]] = []
    skipped_symlinks = 0

    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: unreadable.append((Path(e.filename), str(e)))):
        # Following symlinks would double-count and can loop forever.
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]

        for name in filenames:
            full = Path(dirpath) / name
            if full.is_symlink():
                skipped_symlinks += 1
                continue
            try:
                st = full.stat()
            except OSError as exc:
                unreadable.append((full, exc.strerror or str(exc)))
                continue

            files.append(
                FileRecord(
                    path=full,
                    size=st.st_size,
                    modified=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc),
                    owner=owner_name(st.st_uid),
                )
            )

    return ScanResult(files=files, unreadable=unreadable, skipped_symlinks=skipped_symlinks)


def file_digest(path: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            while chunk := fh.read(HASH_CHUNK_BYTES):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def find_duplicates(files: list[FileRecord]) -> list[list[FileRecord]]:
    """Group byte-identical files.

    Hashing every file would dominate the runtime on a real file server,
    so only files that share a size can be duplicates and get read.
    """
    by_size: dict[int, list[FileRecord]] = defaultdict(list)
    for record in files:
        if record.size > 0:  # empty files are noise, not duplication
            by_size[record.size].append(record)

    groups: list[list[FileRecord]] = []
    for candidates in by_size.values():
        if len(candidates) < 2:
            continue
        by_digest: dict[str, list[FileRecord]] = defaultdict(list)
        for record in candidates:
            digest = file_digest(record.path)
            if digest is not None:
                by_digest[digest].append(record)
        groups.extend(group for group in by_digest.values() if len(group) > 1)

    return sorted(groups, key=lambda g: g[0].size * (len(g) - 1), reverse=True)


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0:
            return f"{value:,.1f} {unit}"
        value /= 1024.0
    return f"{value:,.1f} PB"


def age_distribution(files: list[FileRecord], now: datetime) -> list[tuple[str, int, int]]:
    """Count files and bytes per age bucket, oldest bucket last."""
    labels = [f"< {AGE_BUCKETS[0]} year"]
    labels += [f"{lo}-{hi} years" for lo, hi in zip(AGE_BUCKETS, AGE_BUCKETS[1:])]
    labels.append(f"> {AGE_BUCKETS[-1]} years")

    counts = [0] * len(labels)
    sizes = [0] * len(labels)
    for record in files:
        years = (now - record.modified).days / 365.25
        index = len(AGE_BUCKETS)
        for i, boundary in enumerate(AGE_BUCKETS):
            if years < boundary:
                index = i
                break
        counts[index] += 1
        sizes[index] += record.size

    return list(zip(labels, counts, sizes))


def report(root: Path, result: ScanResult, duplicate_groups: list[list[FileRecord]], stale_years: int, top: int) -> None:
    files = result.files
    now = datetime.now(tz=timezone.utc)
    total_bytes = sum(f.size for f in files)

    print(f"\nDATA INVENTORY — {root}")
    print(f"Scanned {datetime.now():%Y-%m-%d %H:%M}. Read-only: nothing was changed.\n")

    print("WHAT IS THERE")
    print(f"  {len(files):,} files, {human_size(total_bytes)}")
    if result.skipped_symlinks:
        print(f"  {result.skipped_symlinks:,} symlinks skipped (not counted twice)")
    if result.unreadable:
        print(f"  {len(result.unreadable):,} paths could not be read — see the list below")

    wasted = sum(g[0].size * (len(g) - 1) for g in duplicate_groups)
    redundant = sum(len(g) - 1 for g in duplicate_groups)
    print("\nWHAT IS DUPLICATED")
    if duplicate_groups:
        share = wasted / total_bytes * 100 if total_bytes else 0
        print(f"  {redundant:,} redundant copies in {len(duplicate_groups):,} groups")
        print(f"  {human_size(wasted)} recoverable ({share:.1f}% of the total)")
        for group in duplicate_groups[:top]:
            print(f"    {len(group)}x {human_size(group[0].size)}  {group[0].path.name}")
            for record in group[:3]:
                print(f"        {record.path}")
            if len(group) > 3:
                print(f"        ... and {len(group) - 3} more")
    else:
        print("  none found")

    print("\nWHAT NOBODY TOUCHES")
    for label, count, size in age_distribution(files, now):
        share = count / len(files) * 100 if files else 0
        print(f"  {label:<14} {count:>8,} files  {human_size(size):>12}  ({share:4.1f}%)")
    stale = [f for f in files if (now - f.modified).days / 365.25 >= stale_years]
    stale_bytes = sum(f.size for f in stale)
    print(f"  → {len(stale):,} files ({human_size(stale_bytes)}) untouched for {stale_years}+ years")

    print("\nWHO OWNS IT")
    owners = Counter(f.owner for f in files)
    for owner, count in owners.most_common(top):
        share = count / len(files) * 100 if files else 0
        print(f"  {owner:<20} {count:>8,} files ({share:4.1f}%)")
    if len(owners) > top:
        print(f"  ... and {len(owners) - top} more owners")

    if result.unreadable:
        print("\nCOULD NOT BE READ")
        for path, reason in result.unreadable[:top]:
            print(f"  {path}: {reason}")
        if len(result.unreadable) > top:
            print(f"  ... and {len(result.unreadable) - top} more")

    print("\nNothing was deleted. Every number above is a proposal for a decision.\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only data inventory of a directory tree.")
    parser.add_argument("path", type=Path, help="directory to scan")
    parser.add_argument("--stale-years", type=int, default=3, help="age threshold in years (default: 3)")
    parser.add_argument("--top", type=int, default=10, help="how many entries per list (default: 10)")
    args = parser.parse_args(argv)

    root = args.path.expanduser().resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    print(f"Scanning {root} ...", file=sys.stderr)
    result = scan(root)
    print(f"Hashing {len(result.files):,} files for duplicates ...", file=sys.stderr)
    duplicate_groups = find_duplicates(result.files)
    report(root, result, duplicate_groups, args.stale_years, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
