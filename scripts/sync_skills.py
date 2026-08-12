"""Mirror canonical skill bodies into the session-visible discovery surface.

Canonical bodies live in skills/<tier>/<name>/SKILL.md. The harness
discovers skills in .claude/skills/<name>/SKILL.md, so this script mirrors
them flat — and also mirrors the ACTIVE GAME's own skills (working root
and slug read from GAME.local.md) as game-<slug>-<name>, fixing the defect
this repo exists to fix: game skills invisible to the session because they
live in another repo.

Usage:
    python scripts/sync_skills.py           # write the mirror
    python scripts/sync_skills.py --check   # exit 1 on any drift, write nothing
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "skills"
SURFACE = ROOT / ".claude" / "skills"
GAME_LOCAL = ROOT / "GAME.local.md"


def parse_game_local(text: str) -> tuple[Path | None, str | None]:
    """Return (working_root, slug) from GAME.local.md, None where unset."""
    root = slug = None
    m = re.search(r"^\s*-\s*Working root[^:]*:\s*(.+?)\s*$",
                  text, re.MULTILINE | re.IGNORECASE)
    if m and not m.group(1).startswith("<"):
        root = Path(m.group(1).strip())
    m = re.search(r"^\s*-\s*Short slug[^:]*:\s*(.+?)\s*$",
                  text, re.MULTILINE | re.IGNORECASE)
    if m and not m.group(1).startswith("<"):
        slug = re.sub(r"[^a-z0-9-]", "", m.group(1).strip().lower())
    return root, slug


def desired_mirror() -> dict[str, Path]:
    """Map of surface skill name -> canonical SKILL.md path."""
    out: dict[str, Path] = {}
    if CANONICAL.is_dir():
        for body in sorted(CANONICAL.glob("*/*/SKILL.md")):
            name = body.parent.name
            if name in out:
                raise SystemExit(f"duplicate canonical skill name: {name}")
            out[name] = body
    if GAME_LOCAL.is_file():
        root, slug = parse_game_local(GAME_LOCAL.read_text(encoding="utf-8"))
        if root and slug:
            game_skills = root / ".claude" / "skills"
            if game_skills.is_dir():
                for body in sorted(game_skills.glob("*/SKILL.md")):
                    out[f"game-{slug}-{body.parent.name}"] = body
    return out


def current_surface() -> dict[str, Path]:
    if not SURFACE.is_dir():
        return {}
    return {p.parent.name: p for p in sorted(SURFACE.glob("*/SKILL.md"))}


def drift(desired: dict[str, Path], current: dict[str, Path]) -> list[str]:
    problems = []
    for name, src in desired.items():
        dst = current.get(name)
        if dst is None:
            problems.append(f"missing from surface: {name}")
        elif dst.read_bytes() != src.read_bytes():
            problems.append(f"content drift: {name}")
    for name in current:
        if name not in desired:
            problems.append(f"orphan on surface (no canonical source): {name}")
    return problems


def write_mirror(desired: dict[str, Path]) -> None:
    SURFACE.mkdir(parents=True, exist_ok=True)
    for name, src in desired.items():
        dst_dir = SURFACE / name
        dst_dir.mkdir(exist_ok=True)
        shutil.copyfile(src, dst_dir / "SKILL.md")
    for entry in SURFACE.iterdir():
        if entry.is_dir() and entry.name not in desired:
            shutil.rmtree(entry)


def main(argv: list[str]) -> int:
    desired = desired_mirror()
    if "--check" in argv:
        problems = drift(desired, current_surface())
        if problems:
            print("skill surface drift:")
            for p in problems:
                print(f"  {p}")
            return 1
        print(f"surface in sync: {len(desired)} skills")
        return 0
    write_mirror(desired)
    print(f"mirrored {len(desired)} skills into .claude/skills/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
