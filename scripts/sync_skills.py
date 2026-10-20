"""Mirror canonical skill bodies into the session-visible discovery surface.

Canonical bodies live in skills/<tier>/<name>/SKILL.md. The harness
discovers skills in .claude/skills/<name>/SKILL.md, so this script mirrors
them flat. It mirrors the active game's skills and any explicitly preserved
read-only game skill sources from GAME.local.md as game-<slug>-<name>.

Usage:
    python scripts/sync_skills.py           # write the mirror
    python scripts/sync_skills.py --check   # exit 1 on any drift, write nothing
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from gitignored_config import resolve_gitignored  # noqa: E402
from game_config import parse_game_config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "skills"
SURFACES = (ROOT / ".claude" / "skills", ROOT / ".agents" / "skills")
SURFACE = SURFACES[0]  # backward compatibility
GAME_LOCAL = ROOT / "GAME.local.md"


def parse_game_local(text: str) -> tuple[Path | None, str | None]:
    """Return (working_root, slug) from GAME.local.md, None where unset."""
    config = parse_game_config(text)
    return config.working_root, config.slug


def iter_game_skill_bodies(root: Path) -> list[Path]:
    """Game skill bodies: canonical layout first, Claude-native as fill-in.

    An OS-shaped working root keeps skills in skills/<tier>/<name>/SKILL.md
    (same as this repo). A game that only has Claude-native skills keeps
    them in .claude/skills/<name>/SKILL.md. Canonical wins on name clash
    so a generated surface is not preferred over its source.
    """
    found: dict[str, Path] = {}
    skills_root = root / "skills"
    if skills_root.is_dir():
        for body in sorted(skills_root.glob("*/*/SKILL.md")):
            name = body.parent.name
            if name in found:
                raise SystemExit(f"duplicate game skill name: {name}")
            found[name] = body
    claude = root / ".claude" / "skills"
    if claude.is_dir():
        for body in sorted(claude.glob("*/SKILL.md")):
            found.setdefault(body.parent.name, body)
    return [found[k] for k in sorted(found)]


def desired_mirror() -> dict[str, Path]:
    """Map of surface skill name -> canonical SKILL.md path."""
    out: dict[str, Path] = {}
    if CANONICAL.is_dir():
        for body in sorted(CANONICAL.glob("*/*/SKILL.md")):
            name = body.parent.name
            if name in out:
                raise SystemExit(f"duplicate canonical skill name: {name}")
            out[name] = body
    harness = dict(out)
    game_local = resolve_gitignored(GAME_LOCAL, cwd=ROOT)
    if game_local.is_file():
        config = parse_game_config(game_local.read_text(encoding="utf-8"))
        sources: list[tuple[str, Path, bool]] = []
        if config.working_root and config.slug:
            sources.append((config.slug, config.working_root, False))
        sources.extend(
            (slug, root, True)
            for slug, root in config.preserved_game_skill_sources
        )
        for slug, root, preserved in sources:
            bodies = iter_game_skill_bodies(root)
            if preserved and not bodies:
                raise SystemExit(
                    f"preserved game skill source is missing or empty: "
                    f"{slug}={root}")
            for body in bodies:
                name = body.parent.name
                # Identical copy of a harness skill is not "the game's own".
                src = harness.get(name)
                if src is not None and src.read_bytes() == body.read_bytes():
                    continue
                key = f"game-{slug}-{name}"
                if key in out:
                    if out[key].read_bytes() == body.read_bytes():
                        continue
                    raise SystemExit(f"duplicate game skill name: {key}")
                out[key] = body
    return out


def current_surface(surface: Path | None = None) -> dict[str, Path]:
    target = surface if surface is not None else SURFACE
    if not target.is_dir():
        return {}
    return {p.parent.name: p for p in sorted(target.glob("*/SKILL.md"))}


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


def write_mirror(desired: dict[str, Path], surfaces: tuple[Path, ...] | None = None) -> None:
    target_surfaces = surfaces if surfaces is not None else SURFACES
    for surface in target_surfaces:
        surface.mkdir(parents=True, exist_ok=True)
        for name, src in desired.items():
            dst_dir = surface / name
            dst_dir.mkdir(exist_ok=True)
            shutil.copyfile(src, dst_dir / "SKILL.md")
        for entry in surface.iterdir():
            if entry.is_dir() and entry.name not in desired:
                shutil.rmtree(entry)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="sync_skills", description=__doc__.split("\n")[0])
    parser.add_argument(
        "--check", action="store_true",
        help="report discovery-surface drift without writing anything")
    args = parser.parse_args(argv[1:])

    desired = desired_mirror()
    if args.check:
        all_problems = []
        for surface in SURFACES:
            problems = drift(desired, current_surface(surface))
            if problems:
                rel = surface.relative_to(ROOT).as_posix()
                for p in problems:
                    all_problems.append(f"{rel}: {p}")
        if all_problems:
            print("skill surface drift:")
            for p in all_problems:
                print(f"  {p}")
            return 1
        print(f"surface in sync: {len(desired)} skills across {len(SURFACES)} discovery surfaces")
        return 0
    write_mirror(desired)
    print(f"mirrored {len(desired)} skills into {', '.join(s.relative_to(ROOT).as_posix() for s in SURFACES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
