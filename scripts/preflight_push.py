"""Block a git push unless visibility is verified PRIVATE or explicitly granted.

Mechanizes the rule that was violated most expensively in the originating
projects: every push is preceded by a visibility check, and a public push
needs an explicit standing grant. Fail-closed: if visibility cannot be
determined, the push is blocked with instructions, never waved through.

Exit 0 = visibility check passed; per-act authority is separate.
Exit 1 = blocked (reason on stdout).

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
KNOWN_VISIBILITIES = frozenset({"PUBLIC", "PRIVATE", "INTERNAL"})


def canonical_repo_name(value: object) -> bool:
    """Accept one ASCII GitHub owner/name, without URL or whitespace syntax."""
    if not isinstance(value, str):
        return False
    match = re.fullmatch(
        r"([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/"
        r"([A-Za-z0-9_.-]{1,100})", value)
    return bool(match and match.group(2) not in {".", ".."})


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate keys instead of accepting the last supplied identity."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_gh_view(raw: str) -> tuple[str | None, str | None]:
    """Return a recognized visibility and identity, or reject the whole reply."""
    if not isinstance(raw, str):
        return None, None
    try:
        data = json.loads(raw, object_pairs_hook=unique_json_object)
    except (ValueError, TypeError, RecursionError):
        return None, None
    if not isinstance(data, dict) or set(data) != {"visibility", "nameWithOwner"}:
        return None, None
    vis = data.get("visibility")
    name = data.get("nameWithOwner")
    if (not isinstance(vis, str) or not vis.isascii()
            or vis.upper() not in KNOWN_VISIBILITIES
            or not canonical_repo_name(name)):
        return None, None
    return vis.upper(), name


def granted(name_with_owner: str | None, grant_text: str) -> bool:
    if not canonical_repo_name(name_with_owner):
        return False
    target = name_with_owner.lower()
    lines = [ln.strip().lower() for ln in grant_text.splitlines()]
    return target in [ln for ln in lines if ln and not ln.startswith("#")]


def verdict(visibility: str | None, name: str | None,
            grant_text: str,
            grant_path: str = "public-grant.txt") -> tuple[bool, str]:
    """Pure decision core, testable without gh."""
    if not isinstance(visibility, str) or visibility not in KNOWN_VISIBILITIES:
        return False, (
            "PUSH BLOCKED: could not verify repo visibility (gh repo view "
            "failed or returned an unrecognized visibility). A grant cannot "
            "replace a verified visibility result; fix gh auth / remote and "
            "rerun.")
    if not canonical_repo_name(name):
        return False, (
            "PUSH BLOCKED: could not verify a canonical owner/repo identity "
            "for the push destination. Fix gh auth / remote and rerun.")
    if visibility == "PRIVATE":
        return True, (f"visibility preflight passed: {name} is "
                      "PRIVATE; the push still requires per-act user authorization")
    if granted(name, grant_text):
        return True, (f"visibility preflight passed: {name} is "
                      f"{visibility} and is explicitly granted in "
                      f"{grant_path}; the push still requires per-act user "
                      "authorization")
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
        match = re.fullmatch(pattern, raw, re.IGNORECASE | re.ASCII)
        if match and canonical_repo_name(match.group(1)):
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
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
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
            # Pin the host as well as owner/name: GH_HOST or a default enterprise
            # login must not redirect this query away from the github.com remote.
            ["gh", "repo", "view", f"https://github.com/{target_name}",
             "--json", "visibility,nameWithOwner"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30)
        raw = proc.stdout if proc.returncode == 0 else ""
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        raw = ""
    vis, name = parse_gh_view(raw)
    if vis is None or name is None:
        print(f"PUSH BLOCKED: could not verify repo visibility and identity "
              f"for {target_name} (gh repo view failed or returned invalid data).")
        return 1
    if name.lower() != target_name.lower():
        print(f"PUSH BLOCKED: gh repo view returned {name}, which does not "
              f"match named push destination {target_name}.")
        return 1
    grant_path = str(GRANT_FILE)
    try:
        grant_file = resolve_gitignored(GRANT_FILE, cwd=GRANT_FILE.parent)
        grant_path = str(grant_file)
        if grant_file.is_file():
            grant_text = grant_file.read_text(encoding="utf-8")
        else:
            grant_text = ""
            grant_path = f"{grant_file} (absent)"
    except (OSError, UnicodeError):
        print(f"PUSH BLOCKED: could not read visibility grant configuration "
              f"at {grant_path}.")
        return 1
    ok, message = verdict(vis, name, grant_text, grant_path=grant_path)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
