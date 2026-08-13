"""Block a git push unless the target repo is verified PRIVATE.

Mechanizes the rule that was violated most expensively in the originating
projects: every push is preceded by a visibility check, and a public push
needs an explicit standing grant. Fail-closed: if visibility cannot be
determined, the push is blocked with instructions, never waved through.

Exit 0 = push may proceed. Exit 1 = blocked (reason on stdout).

Override path: add the repo's exact "owner/name" on its own line in
public-grant.txt at this repo's root (gitignored) after the user
explicitly authorizes public pushes for that repo. Verdicts name the
resolved path of that file: gitignored config is per-checkout, and a
worktree starts without it (2026-08-13).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from gitignored_config import resolve_gitignored  # noqa: E402

GRANT_FILE = Path(__file__).resolve().parent.parent / "public-grant.txt"


def parse_gh_view(raw: str) -> tuple[str | None, str | None]:
    """Return (visibility, name_with_owner) from `gh repo view --json` output."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, None
    vis = data.get("visibility")
    name = data.get("nameWithOwner")
    return (vis.upper() if isinstance(vis, str) else None,
            name if isinstance(name, str) else None)


def granted(name_with_owner: str | None, grant_text: str) -> bool:
    if not name_with_owner:
        return False
    lines = [ln.strip() for ln in grant_text.splitlines()]
    return name_with_owner in [ln for ln in lines if ln and not ln.startswith("#")]


def verdict(visibility: str | None, name: str | None,
            grant_text: str,
            grant_path: str = "public-grant.txt") -> tuple[bool, str]:
    """Pure decision core, testable without gh."""
    if visibility == "PRIVATE":
        return True, f"push allowed: {name or 'repo'} is PRIVATE"
    if granted(name, grant_text):
        return True, (f"push allowed: {name} is {visibility or 'UNKNOWN'} "
                      f"but explicitly granted in {grant_path}")
    if visibility is None:
        return False, (
            "PUSH BLOCKED: could not verify repo visibility (gh repo view "
            "failed or returned no data). The standing rule is that every "
            "push is preceded by a PRIVATE check. Fix gh auth / remote, or "
            "have the user grant this repo in "
            f"{grant_path}.")
    return False, (
        f"PUSH BLOCKED: {name or 'this repo'} is {visibility}, not PRIVATE. "
        "Publishing to a non-private repo is a separately authorized act. "
        "If the user has explicitly authorized it, add the exact "
        f"'owner/name' line to {grant_path} and rerun.")


def main(argv: list[str]) -> int:
    repo_dir = argv[1] if len(argv) > 1 else "."
    try:
        proc = subprocess.run(
            ["gh", "repo", "view", "--json", "visibility,nameWithOwner"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30)
        raw = proc.stdout if proc.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        raw = ""
    vis, name = parse_gh_view(raw)
    grant_file = resolve_gitignored(GRANT_FILE, cwd=GRANT_FILE.parent)
    if grant_file.is_file():
        grant_text = grant_file.read_text(encoding="utf-8")
        grant_path = str(grant_file)
    else:
        grant_text = ""
        grant_path = f"{GRANT_FILE} (absent)"
    ok, message = verdict(vis, name, grant_text, grant_path=grant_path)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
