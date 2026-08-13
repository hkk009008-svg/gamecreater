"""Resolve gitignored config that does not follow a branch into a worktree.

Gitignored files (public-grant.txt, scrub_terms.local.txt) live in one
checkout. A worktree of the same repo starts with those tiers absent:
the push guard then fail-closes (visible), the scrub gate silently
degrades to the generic patterns (the dangerous sibling). Paid for
2026-08-13.

If `path` is missing here, try the primary checkout (the directory that
contains `git rev-parse --git-common-dir`). Callers must still name the
resolved path in every verdict so a session can see which tree it read.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def resolve_gitignored(path: Path, cwd: Path | None = None) -> Path:
    """Return `path` if it exists, else the same filename in the primary tree.

    Missing in both trees returns the original path (still absent) so the
    caller can say so. Never invent a file.
    """
    if path.is_file():
        return path
    probe_cwd = cwd if cwd is not None else path.parent
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=probe_cwd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return path
    if proc.returncode != 0:
        return path
    raw = proc.stdout.strip()
    if not raw:
        return path
    common = Path(raw)
    if not common.is_absolute():
        common = probe_cwd / common
    try:
        candidate = common.resolve().parent / path.name
    except OSError:
        return path
    try:
        if candidate.is_file() and candidate.resolve() != path.resolve():
            return candidate
    except OSError:
        return path
    return path
