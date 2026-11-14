"""A static site as a deploy target: plan what would change, upload exactly what was approved, prove what is served.

A site is a folder of files and a place that serves them. The place is a `Target`: a directory (a preview beside the
source, a test) or an FTP account over TLS (a shared hoster). Nothing here knows a particular site; a site is described
by a small JSON file kept with the site, never in this repository (REQ-008):

    {
      "source": "website",
      "target": {"kind": "ftps", "host": "ftp.example.org", "root": "example.org"},
      "url": "https://example.org",
      "exclude": ["README.md", "drafts/**"],
      "protected": ["secrets.php", "_data/**"],
      "must_not_serve": ["_data/list.csv"]
    }

Three steps, each one command, each printing a report that can be laid into a case:

    python3 site.py plan   site.json                 what is new, changed, the same; what only the server has
    python3 site.py apply  site.json --plan <id>     upload the plan with that id, keep what it replaces
    python3 site.py verify site.json                 fetch every file over HTTP and compare it with the source
    python3 site.py publish site.json                all three for a person at a terminal: plan, one question, apply, verify

The rules that used to live in a deploy guide and in somebody's head:
- **The plan is the gate.** `apply` takes the id of a plan a person has read. If the source or the server changed
  since, the id no longer matches and nothing is uploaded.
- **Nothing is ever deleted on the server.** What only the server has is listed and left alone.
- **Protected paths are never written**, not even when the source carries a file of that name.
- **What is replaced is kept**: before a file is overwritten its served version is saved beside the report.
- **A file arrives whole**: it is uploaded under a temporary name and renamed.
- **Verify asks slowly.** The first real run fetched 64 files three times in a few minutes and the hoster locked the
  address out of its web ports. There is a pause between two requests.

Credentials come from the environment (`SITE_USER`, `SITE_PASSWORD`: a run is handed them for its duration) or from the
file the site description names in `target.secret` (two lines: user, password; outside every repository). Standard
library only, and no import from the rest of casefile: the module can be run on its own.
"""

from __future__ import annotations

import argparse
import fnmatch
import ftplib
import hashlib
import io
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Protocol

AGENT = "site-verify/1"
ALWAYS_EXCLUDED = (".DS_Store", "**/.DS_Store", ".git/**", "**/*.tmp-upload")
PAUSE = 0.4  # seconds between two requests of a verify: a shared hoster locks out an address that asks too fast
NOT_COMPARABLE = (".php", ".htaccess")  # executed or withheld by the server: served bytes are not the source bytes


class SiteError(Exception):
    """A site cannot be planned, uploaded or verified as described; the message says what to change."""


# ── the description of a site ────────────────────────────────────────────────────────────────────────────────────


@dataclass
class Site:
    source: Path
    target: dict
    url: str = ""
    exclude: list[str] = field(default_factory=list)
    protected: list[str] = field(default_factory=list)
    must_not_serve: list[str] = field(default_factory=list)
    file_mode: str = "644"
    dir_mode: str = "755"

    @classmethod
    def load(cls, path: Path) -> "Site":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SiteError(f"the site description {path} cannot be read: {e}") from e
        unknown = set(raw) - {"source", "target", "url", "exclude", "protected", "must_not_serve", "file_mode", "dir_mode"}
        if unknown:
            raise SiteError(f"{path}: unknown keys {sorted(unknown)}")
        if "source" not in raw or "target" not in raw:
            raise SiteError(f"{path}: 'source' and 'target' are required")
        source = (path.parent / raw.pop("source")).resolve()
        if not source.is_dir():
            raise SiteError(f"{path}: the source folder {source} does not exist")
        return cls(source=source, **raw)


def matches(path: str, patterns) -> bool:
    """`dir/**` covers everything below dir; any other pattern is matched against the whole path and against the name."""
    name = PurePosixPath(path).name
    for p in patterns:
        if p.endswith("/**") and (path == p[:-3] or path.startswith(p[:-2])):
            return True
        if p.startswith("**/") and fnmatch.fnmatch(name, p[3:]):
            return True
        if fnmatch.fnmatch(path, p) or ("/" not in p and name == p):
            return True
    return False


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_files(site: Site) -> dict[str, bytes]:
    """Every file of the source that belongs on the server, by its path below the source."""
    out = {}
    for f in sorted(site.source.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(site.source).as_posix()
        if matches(rel, ALWAYS_EXCLUDED) or matches(rel, site.exclude) or matches(rel, site.protected):
            continue
        out[rel] = f.read_bytes()
    return out


# ── targets ──────────────────────────────────────────────────────────────────────────────────────────────────────


class Target(Protocol):
    def listing(self) -> dict[str, int]: ...          # path → size, every file below the root
    def read(self, path: str) -> bytes: ...
    def write(self, path: str, data: bytes) -> None: ...  # creates folders, arrives whole
    def chmod(self, path: str, mode: str) -> bool: ...    # False where the place cannot


class DirTarget:
    """A directory: a preview beside the source, the other end in a test."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def listing(self) -> dict[str, int]:
        if not self.root.is_dir():
            return {}
        return {f.relative_to(self.root).as_posix(): f.stat().st_size for f in sorted(self.root.rglob("*")) if f.is_file()}

    def read(self, path: str) -> bytes:
        return (self.root / path).read_bytes()

    def write(self, path: str, data: bytes) -> None:
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp-upload")
        tmp.write_bytes(data)
        tmp.replace(dest)

    def chmod(self, path: str, mode: str) -> bool:
        os.chmod(self.root / path, int(mode, 8))
        return True


class _ReusingTLS(ftplib.FTP_TLS):
    """Many FTP servers demand that the data connection resumes the TLS session of the control connection."""

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


class FtpsTarget:
    """An FTP account over explicit TLS, as shared hosters offer it. `root` is the site's folder in the account."""

    def __init__(self, host: str, user: str, password: str, root: str = "", port: int = 21, timeout: int = 60):
        self.root = root.strip("/")
        self._made: set[str] = set()
        try:
            self.ftp = _ReusingTLS(context=ssl.create_default_context(), timeout=timeout)
            self.ftp.connect(host, port)
            self.ftp.login(user, password)
            self.ftp.prot_p()
        except (OSError, ftplib.Error) as e:
            raise SiteError(f"no connection to the target: {e}") from e

    def _abs(self, path: str) -> str:
        return "/" + "/".join(p for p in (self.root, path) if p)

    def listing(self) -> dict[str, int]:
        out: dict[str, int] = {}

        def walk(rel: str) -> None:
            try:
                entries = list(self.ftp.mlsd(self._abs(rel), facts=["type", "size"]))
            except ftplib.Error as e:
                raise SiteError(f"the target cannot list {rel or 'its root'}: {e}") from e
            for name, facts in entries:
                if name in (".", ".."):
                    continue
                child = f"{rel}/{name}" if rel else name
                if facts.get("type") == "dir":
                    self._made.add(child)
                    walk(child)
                elif facts.get("type") == "file":
                    out[child] = int(facts.get("size", -1))

        walk("")
        return out

    def read(self, path: str) -> bytes:
        buf = io.BytesIO()
        self.ftp.retrbinary("RETR " + self._abs(path), buf.write)
        return buf.getvalue()

    def _mkdirs(self, folder: str) -> None:
        parts = [p for p in folder.split("/") if p]
        for i in range(1, len(parts) + 1):
            sub = "/".join(parts[:i])
            if sub in self._made:
                continue
            try:
                self.ftp.mkd(self._abs(sub))
            except ftplib.error_perm:
                pass  # it is there already
            self._made.add(sub)

    def write(self, path: str, data: bytes) -> None:
        self._mkdirs(str(PurePosixPath(path).parent) if "/" in path else "")
        tmp = self._abs(path) + ".tmp-upload"
        self.ftp.storbinary("STOR " + tmp, io.BytesIO(data))
        self.ftp.rename(tmp, self._abs(path))

    def chmod(self, path: str, mode: str) -> bool:
        try:
            self.ftp.sendcmd(f"SITE CHMOD {mode} {self._abs(path)}")
            return True
        except ftplib.Error:
            return False

    def close(self) -> None:
        try:
            self.ftp.quit()
        except (OSError, ftplib.Error):
            pass


def credentials(target: dict, base: Path) -> tuple[str, str]:
    user, password = os.environ.get("SITE_USER", ""), os.environ.get("SITE_PASSWORD", "")
    if user and password:
        return user, password
    secret = target.get("secret")
    if not secret:
        raise SiteError("no credentials: set SITE_USER and SITE_PASSWORD, or name a file in target.secret")
    f = Path(os.path.expanduser(secret))
    f = f if f.is_absolute() else base / f
    try:
        lines = [line.strip() for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError as e:
        raise SiteError(f"the secret file {f} cannot be read: {e}") from e
    if len(lines) < 2:
        raise SiteError(f"the secret file {f} needs two lines: user, password")
    return lines[0], lines[1]


def open_target(site: Site, base: Path) -> Target:
    t = site.target
    kind = t.get("kind")
    if kind == "dir":
        p = Path(os.path.expanduser(t.get("path", "")))
        return DirTarget(p if p.is_absolute() else base / p)
    if kind == "ftps":
        user, password = credentials(t, base)
        return FtpsTarget(t["host"], user, password, t.get("root", ""), int(t.get("port", 21)))
    raise SiteError(f"unknown target kind {kind!r}: 'dir' or 'ftps'")


# ── plan ─────────────────────────────────────────────────────────────────────────────────────────────────────────


@dataclass
class Plan:
    id: str
    new: list[str]
    changed: list[str]
    same: list[str]
    server_only: list[str]      # left alone, never deleted
    protected: list[str]        # on the server, never written
    held_back: list[str]        # in the source under a protected name: not uploaded
    bytes: int

    @property
    def uploads(self) -> list[str]:
        return self.new + self.changed


def make_plan(site: Site, target: Target) -> Plan:
    local = local_files(site)
    remote = target.listing()
    new, changed, same = [], [], []
    for path, data in local.items():
        if path not in remote:
            new.append(path)
        elif remote[path] == len(data) and digest(target.read(path)) == digest(data):
            same.append(path)
        else:
            changed.append(path)
    held_back = sorted(
        f.relative_to(site.source).as_posix()
        for f in site.source.rglob("*")
        if f.is_file() and matches(f.relative_to(site.source).as_posix(), site.protected)
    )
    rest = [p for p in sorted(remote) if p not in local and not p.endswith(".tmp-upload")]
    protected = [p for p in rest if matches(p, site.protected)]
    server_only = [p for p in rest if p not in protected]
    # The id names what would be written and onto what: any change on either side makes it another plan.
    basis = [("new", p, digest(local[p])) for p in new] + [("changed", p, digest(local[p]), remote[p]) for p in changed]
    plan_id = digest(json.dumps(basis, sort_keys=True).encode())[:12]
    return Plan(plan_id, new, changed, same, server_only, protected, held_back, sum(len(local[p]) for p in new + changed))


# ── apply ────────────────────────────────────────────────────────────────────────────────────────────────────────


@dataclass
class Applied:
    plan: str
    uploaded: list[str]
    kept: str                   # where the replaced files were saved ("" when nothing was replaced)
    modes_not_set: list[str]


def apply_plan(site: Site, target: Target, approved: str, keep: Path, log: Callable[[str], None] = lambda s: None) -> Applied:
    plan = make_plan(site, target)
    if plan.id != approved:
        raise SiteError(
            f"the approved plan is {approved}, the plan now is {plan.id}: the source or the server changed since. "
            "Nothing was uploaded. Read the new plan and approve it."
        )
    local = local_files(site)
    kept = ""
    if plan.changed:
        folder = keep / f"replaced-{plan.id}"
        for path in plan.changed:
            dest = folder / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(target.read(path))
        kept = str(folder)
    modes_not_set, folders = [], set()
    for path in plan.uploads:
        if matches(path, site.protected):  # cannot happen (local_files leaves them out); the rule is worth a second lock
            raise SiteError(f"{path} is protected and was about to be written")
        target.write(path, local[path])
        if not target.chmod(path, site.file_mode):
            modes_not_set.append(path)
        parent = PurePosixPath(path).parent
        while str(parent) not in (".", "") and str(parent) not in folders:
            folders.add(str(parent))
            parent = parent.parent
        log(f"  up  {path}")
    for folder in sorted(folders):
        if not target.chmod(folder, site.dir_mode):
            modes_not_set.append(folder + "/")
    return Applied(plan.id, plan.uploads, kept, modes_not_set)


# ── verify ───────────────────────────────────────────────────────────────────────────────────────────────────────


def http_get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (urllib.error.URLError, OSError) as e:
        raise SiteError(f"{url} cannot be reached: {e}") from e


@dataclass
class Verified:
    ok: bool
    served: int
    differs: list[str]          # served, but not the bytes of the source
    missing: list[str]          # "path (status)"
    exposed: list[str]          # must not be served, and is
    not_compared: list[str]


def verify(site: Site, fetch: Callable[[str], tuple[int, bytes]] | None = None, pause: float = PAUSE) -> Verified:
    if not site.url:
        raise SiteError("the site description has no 'url': nothing to verify against")
    base = site.url.rstrip("/")
    if fetch is None:
        def fetch(url: str) -> tuple[int, bytes]:
            time.sleep(pause)
            return http_get(url)
    served, differs, missing, skipped = 0, [], [], []
    for path, data in local_files(site).items():
        if path.endswith(NOT_COMPARABLE) or PurePosixPath(path).name.startswith("."):
            skipped.append(path)
            continue
        status, body = fetch(f"{base}/{urllib.request.quote(path)}")
        if status != 200:
            missing.append(f"{path} ({status})")
        elif digest(body) != digest(data):
            differs.append(path)
        else:
            served += 1
    exposed = [p for p in site.must_not_serve if fetch(f"{base}/{urllib.request.quote(p)}")[0] not in (401, 403, 404)]
    return Verified(not (differs or missing or exposed), served, differs, missing, exposed, skipped)


# ── command line ─────────────────────────────────────────────────────────────────────────────────────────────────


def _show(title: str, paths: list[str], limit: int = 40) -> None:
    if not paths:
        return
    print(f"{title} ({len(paths)})")
    for p in paths[:limit]:
        print(f"  {p}")
    if len(paths) > limit:
        print(f"  … and {len(paths) - limit} more")


def _print_plan(p: Plan) -> None:
    _show("new", p.new)
    _show("changed", p.changed)
    _show("only on the server, left alone", p.server_only)
    _show("protected on the server, never written", p.protected)
    _show("in the source under a protected name, not uploaded", p.held_back)
    print(f"the same: {len(p.same)}   to upload: {len(p.uploads)} files, {p.bytes / 1e6:.1f} MB")
    print(f"plan {p.id}" if p.uploads else "nothing to upload")


def _print_applied(a: Applied) -> None:
    print(f"uploaded: {len(a.uploaded)} files (plan {a.plan})")
    if a.kept:
        print(f"replaced files kept in {a.kept}")
    _show("mode could not be set", a.modes_not_set)


def _print_verified(v: Verified) -> None:
    print(f"served as in the source: {v.served}")
    _show("served, but different from the source", v.differs)
    _show("not served", v.missing)
    _show("served, and must not be", v.exposed)
    _show("not compared (executed or withheld by the server)", v.not_compared)
    print("VERIFIED" if v.ok else "NOT VERIFIED")


def _ask(plan: Plan) -> bool:
    return input("Upload this plan? (y/n) ").strip().lower() in ("y", "yes", "j", "ja")


def main(argv: list[str] | None = None, confirm: Callable[[Plan], bool] = _ask, fetch=None) -> int:
    ap = argparse.ArgumentParser(description="A static site as a deploy target: plan, apply an approved plan, verify.")
    ap.add_argument("step", choices=["plan", "apply", "verify", "publish"])
    ap.add_argument("site", type=Path, help="the site description (JSON), kept with the site")
    ap.add_argument("--plan", help="apply: the id of the plan that was read and approved")
    ap.add_argument("--report", type=Path, help="write the result as JSON to this file")
    ap.add_argument("--keep", type=Path, help="apply, publish: where replaced files are saved (default: beside the description)")
    args = ap.parse_args(argv)
    result: dict = {"step": args.step}
    code = 0
    try:
        site = Site.load(args.site)
        base = args.site.resolve().parent
        keep = args.keep or base / ".site-kept"
        if args.step == "verify":
            v = verify(site, fetch)
            _print_verified(v)
            result.update(asdict(v))
            code = 0 if v.ok else 1
        else:
            target = open_target(site, base)
            try:
                if args.step == "plan":
                    p = make_plan(site, target)
                    _print_plan(p)
                    result.update(asdict(p))
                elif args.step == "apply":
                    if not args.plan:
                        raise SiteError("apply needs --plan <id>: the id of the plan that was read")
                    a = apply_plan(site, target, args.plan, keep, print)
                    _print_applied(a)
                    result.update(asdict(a))
                else:  # publish: the three steps with one question in between, the person at the terminal is the gate
                    p = make_plan(site, target)
                    _print_plan(p)
                    result["plan"] = asdict(p)
                    if p.uploads:
                        if not confirm(p):
                            print("nothing uploaded")
                            result["approved"] = False
                        else:
                            result["approved"] = True
                            a = apply_plan(site, target, p.id, keep, print)
                            _print_applied(a)
                            result["applied"] = asdict(a)
                    if site.url and result.get("approved", True):
                        v = verify(site, fetch)
                        _print_verified(v)
                        result["verified"] = asdict(v)
                        code = 0 if v.ok else 1
            finally:
                if hasattr(target, "close"):
                    target.close()
    except SiteError as e:
        print(f"site: {e}", file=sys.stderr)
        return 2
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
