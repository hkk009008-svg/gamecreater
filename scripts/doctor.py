"""Instant session orientation and health diagnostic for gamecreater.

Usage:
    python scripts/doctor.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import check_editor_clear  # noqa: E402
import sync_skills  # noqa: E402
from gitignored_config import resolve_gitignored  # noqa: E402


def check_game_roots() -> tuple[bool, list[str]]:
    game_local = resolve_gitignored(ROOT / "GAME.local.md", cwd=ROOT)
    if not game_local.is_file():
        return False, ["GAME.local.md absent (copy templates/GAME.local.template.md)"]

    text = game_local.read_text(encoding="utf-8")
    root, slug = sync_skills.parse_game_local(text)
    notes = [f"Game slug: {slug or 'unset'}"]
    if root:
        exists = root.is_dir()
        notes.append(f"Working root: {root} [{'OK' if exists else 'NOT FOUND'}]")
    else:
        notes.append("Working root: unset")
    return True, notes


def check_active_arc() -> list[str]:
    game_local = resolve_gitignored(ROOT / "GAME.local.md", cwd=ROOT)
    if not game_local.is_file():
        return ["NOW.md: unknown (no GAME.local.md)"]

    text = game_local.read_text(encoding="utf-8")
    m = re.search(r"^\s*-\s*NOW\.md[^:]*:\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not m or m.group(1).startswith("<"):
        return ["NOW.md path: unset in GAME.local.md"]

    now_path = Path(m.group(1).strip())
    if not now_path.is_file():
        return [f"NOW.md: NOT FOUND at {now_path}"]

    now_text = now_path.read_text(encoding="utf-8")
    arc_m = re.search(r"^## Current arc\s*\n+([^#\n][^\n]+)", now_text, re.MULTILINE)
    action_m = re.search(r"^## Next executable action\s*\n+([^#\n][^\n]+)", now_text, re.MULTILINE)
    out = [f"NOW.md: {now_path}"]
    if arc_m:
        out.append(f"  Arc: {arc_m.group(1).strip()[:80]}")
    if action_m:
        out.append(f"  Next Action: {action_m.group(1).strip()[:80]}")
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    print("=== gamecreater session doctor ===")
    ok, root_notes = check_game_roots()
    for n in root_notes:
        print(f"  {n}")

    # Check skills mirror
    desired = sync_skills.desired_mirror()
    drift_count = 0
    for s in sync_skills.SURFACES:
        problems = sync_skills.drift(desired, sync_skills.current_surface(s))
        if problems:
            drift_count += len(problems)
    if drift_count:
        print(f"  Skills: DRIFT DETECTED ({drift_count} issues) -> auto-syncing...")
        sync_skills.write_mirror(desired)
        print(f"  Skills: synchronized {len(desired)} skills across {len(sync_skills.SURFACES)} discovery surfaces")
    else:
        print(f"  Skills: {len(desired)} skills in sync across {len(sync_skills.SURFACES)} discovery surfaces")

    # Check editor process
    try:
        procs = check_editor_clear.list_processes()
        hits = check_editor_clear.matching_processes(procs, "UnrealEditor")
        if hits:
            print(f"  Editor: RUNNING ({', '.join(hits)}) [Headless launch blocked]")
        else:
            print("  Editor: clear (no UnrealEditor running)")
    except Exception as e:
        print(f"  Editor check: failed ({e})")

    # Active Arc
    print("\n--- Active State ---")
    for line in check_active_arc():
        print(f"  {line}")

    print("==================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
