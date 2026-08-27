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
import re
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
    target = name_with_owner.strip().lower()
    lines = [ln.strip().lower() for ln in grant_text.splitlines()]
    return target in [ln for ln in lines if ln and not ln.startswith("#")]


def verdict(visibility: str | None, name: str | None,
            grant_text: str,
            grant_path: str = "public-grant.txt") -> tuple[bool, str]:
    """Pure decision core, testable without gh."""
    if visibility == "PRIVATE":
        return True, (f"visibility preflight passed: {name or 'repo'} is "
                      "PRIVATE; the push still requires per-act user authorization")
    if granted(name, grant_text):
        return True, (f"visibility preflight passed: {name} is "
                      f"{visibility or 'UNKNOWN'} and is explicitly granted in "
                      f"{grant_path}; the push still requires per-act user "
                      "authorization")
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


def repo_name_from_url(raw: str) -> str | None:
    """Parse owner/name only when the destination is actually github.com."""
    raw = raw.strip()
    patterns = (
        r"^(?:https?|ssh)://(?:[^/@]+@)?github\.com/"
        r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
        r"^(?:[^@/:]+@)?github\.com:"
        r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, raw, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def repo_name_from_git(repo_dir: str, remote: str = "origin") -> str | None:
    """Resolve one exact named push destination; ambiguity fails closed."""
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "--push", "--all", remote],
            cwd=repo_dir, capture_output=True, text=True, timeout=10)
        destinations = [line.strip() for line in proc.stdout.splitlines()
                        if line.strip()]
        if proc.returncode == 0 and len(destinations) == 1:
            return repo_name_from_url(destinations[0])
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    repo_dir = argv[1] if len(argv) > 1 else "."
    remote = argv[2] if len(argv) > 2 else "origin"
    target_name = repo_name_from_git(repo_dir, remote)
    if not target_name:
        print(f"PUSH BLOCKED: could not resolve named push remote {remote!r} "
              f"in {repo_dir!r} to an owner/repo identity.")
        return 1
    try:
        proc = subprocess.run(
            ["gh", "repo", "view", target_name,
             "--json", "visibility,nameWithOwner"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30)
        raw = proc.stdout if proc.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        raw = ""
    vis, name = parse_gh_view(raw)
    if name and name.lower() != target_name.lower():
        vis, name = None, target_name
    elif not name:
        name = target_name
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
