"""Append-only check for the lessons inboxes.

A lesson is paid for once and dies silently if a later session rewrites or
deletes it -- and nothing in this repo would have noticed: `session_start`
reports counts, and a rewrite that keeps the count is invisible. The
mechanism here is the same one the run supervisor uses for artifacts:
compare against a baseline nobody can quietly edit, which for a versioned
file is its own committed HEAD.

APPEND-ONLY holds iff the committed text is a byte-prefix of the working
text after newline normalization (this repo's git converts LF to CRLF on
touch, so raw bytes would false-positive on every checkout). A file with
no committed baseline is reported NO_BASELINE, never scored as a
violation: an unborn inbox is not a corrupted one.

The DISTILL exception: `distill-an-arc` legitimately rewrites the inbox
(sweep + marker). It runs on the user's go and commits immediately, so
the window where this check reports a violation is exactly the window
where a distill is in progress -- and the check says so rather than
crying corruption.

Bounded-ness stays where it already lives: `session_start` warns on
distill age and entry count. This module exposes the counts it needs.

Usage: python scripts/check_lessons_inbox.py [--repo ROOT --file REL]...
       (no args: the harness inbox, plus the game inbox from GAME.local.md)
Exit 0: every configured inbox append-only (or NO_BASELINE).
Exit 1: violation, missing/unconfigured inbox, or an unreadable repository.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from game_config import load_game_config

ROOT = Path(__file__).resolve().parent.parent
ENTRY_RE = re.compile(r"^-\s+20\d\d-\d\d-\d\d", re.M)


@dataclass(frozen=True)
class InboxDiscovery:
    status: str
    detail: str
    repo_root: Path | None = None
    inbox: Path | None = None


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


def committed_text(repo_root: Path, relpath: str) -> str | None:
    """HEAD's copy of relpath, or None when there is no baseline."""
    try:
        p = subprocess.run(
            ["git", "-C", str(repo_root), "show",
             "HEAD:%s" % relpath.replace("\\", "/")],
            capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", errors="replace")


def append_only_verdict(committed: str | None,
                        current: str) -> tuple[str, str]:
    """('OK'|'NO_BASELINE'|'VIOLATION', detail)."""
    if committed is None:
        return "NO_BASELINE", "no committed copy to compare against"
    old = normalize(committed)
    new = normalize(current)
    if new.startswith(old):
        added = len(ENTRY_RE.findall(new[len(old):]))
        return "OK", "+%d entr%s since HEAD" % (added,
                                                "y" if added == 1 else "ies")
    # Name the first divergent line -- a verdict without a location sends
    # the reader diffing by hand.
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    for i, (a, b) in enumerate(zip(old_lines, new_lines), 1):
        if a != b:
            return "VIOLATION", (
                "line %d changed:\n  HEAD: %r\n  now : %r\n"
                "Committed lessons were edited or deleted. If this is a "
                "distill-an-arc sweep in progress, commit it; anything else "
                "is a lesson dying." % (i, a[:100], b[:100]))
    return "VIOLATION", (
        "working copy is SHORTER than HEAD (%d -> %d lines): committed "
        "lessons were deleted" % (len(old_lines), len(new_lines)))


def entry_count(text: str) -> int:
    return len(ENTRY_RE.findall(text))


def game_inbox() -> InboxDiscovery:
    """Discover the configured game inbox, naming every failure state."""
    requested = ROOT / "GAME.local.md"
    try:
        config = load_game_config(requested)
    except Exception as exc:                                  # noqa: BLE001
        return InboxDiscovery(
            "ERROR", f"could not load {requested}: {type(exc).__name__}: {exc}")
    if not config.source.is_file():
        return InboxDiscovery(
            "UNCONFIGURED", f"GAME.local.md not found (looked at {config.source})")
    if config.lessons is None:
        return InboxDiscovery(
            "UNCONFIGURED", f"Lessons inbox is not set in {config.source}")

    inbox = config.lessons
    if not inbox.is_file():
        return InboxDiscovery(
            "MISSING", f"configured inbox does not exist: {inbox}", inbox=inbox)
    try:
        probe = subprocess.run(
            ["git", "-C", str(inbox.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=30)
    except Exception as exc:                                  # noqa: BLE001
        return InboxDiscovery(
            "ERROR", f"could not find repository for {inbox}: "
                     f"{type(exc).__name__}: {exc}", inbox=inbox)
    root = probe.stdout.strip()
    if probe.returncode != 0 or not root:
        detail = probe.stderr.strip() or "git rev-parse returned no repository"
        return InboxDiscovery(
            "ERROR", f"could not find repository for {inbox}: {detail}",
            inbox=inbox)
    return InboxDiscovery(
        "OK", f"configured by {config.source}", Path(root), inbox)


def check_one(repo_root: Path, inbox: Path) -> tuple[str, str, int]:
    rel = inbox.resolve().relative_to(repo_root.resolve()).as_posix()
    current = inbox.read_text(encoding="utf-8", errors="replace")
    verdict, detail = append_only_verdict(
        committed_text(repo_root, rel), current)
    return verdict, detail, entry_count(current)


def main(argv: list[str]) -> int:
    pairs: list[tuple[str, Path, Path]] = []
    worst = 0
    args = argv[1:]
    while args:
        if args[0] == "--repo" and len(args) >= 4 and args[2] == "--file":
            root = Path(args[1])
            pairs.append((root.name, root, root / args[3]))
            args = args[4:]
        else:
            print("usage: check_lessons_inbox.py "
                  "[--repo ROOT --file REL]...", file=sys.stderr)
            return 2
    if not pairs:
        pairs.append(("harness", ROOT, ROOT / "memory" / "LESSONS.md"))
        game = game_inbox()
        if game.status == "OK":
            assert game.repo_root is not None and game.inbox is not None
            pairs.append(("game", game.repo_root, game.inbox))
        else:
            print(f"game: {game.status} ({game.detail})")
            worst = max(worst, 1)

    for label, root, inbox in pairs:
        if not inbox.is_file():
            print(f"{label}: MISSING at {inbox}")
            worst = max(worst, 1)
            continue
        try:
            verdict, detail, n = check_one(root, inbox)
        except Exception as exc:                               # noqa: BLE001
            print(f"{label}: ERROR ({type(exc).__name__}: {exc})")
            worst = max(worst, 1)
            continue
        print(f"{label}: {verdict} ({n} entries; {detail.splitlines()[0]})")
        if verdict == "VIOLATION":
            print(detail)
            worst = max(worst, 1)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
