"""Read the active game's machine-local binding from ``GAME.local.md``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gitignored_config import resolve_gitignored


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "GAME.local.md"


def _value(text: str, label: str) -> str | None:
    """Read one ``- Label (optional detail): value`` field."""
    match = re.search(
        rf"^\s*-\s*{re.escape(label)}(?:\s*\([^)]*\))?\s*:\s*(.*?)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).strip().strip("`")
    return None if not value or value.startswith("<") else value


def _path(text: str, label: str) -> Path | None:
    value = _value(text, label)
    return Path(value) if value else None


@dataclass(frozen=True)
class GameConfig:
    source: Path
    name: str | None = None
    slug: str | None = None
    working_root: Path | None = None
    project_root: Path | None = None
    engine_root: Path | None = None
    now: Path | None = None
    lessons: Path | None = None

    @property
    def project_dir(self) -> Path | None:
        if self.project_root is None:
            return None
        return (self.project_root.parent
                if self.project_root.suffix.lower() == ".uproject"
                else self.project_root)

    @property
    def uproject(self) -> Path | None:
        """Return the sole configured ``.uproject``; ambiguity is an error."""
        root = self.project_root
        if root is None:
            return None
        if root.suffix.lower() == ".uproject":
            return root
        if not root.is_dir():
            return None
        matches = sorted(root.glob("*.uproject"))
        return matches[0] if len(matches) == 1 else None

    @property
    def evidence_root(self) -> Path | None:
        return self.project_dir / "Experiments" if self.project_dir else None


def parse_game_config(text: str, source: Path = DEFAULT_PATH) -> GameConfig:
    slug = _value(text, "Short slug")
    if slug:
        slug = re.sub(r"[^a-z0-9-]", "", slug.lower()) or None
    return GameConfig(
        source=source,
        name=_value(text, "Game name"),
        slug=slug,
        working_root=_path(text, "Working root"),
        project_root=_path(text, "Project root"),
        engine_root=_path(text, "Engine root"),
        now=_path(text, "NOW.md"),
        lessons=_path(text, "Lessons inbox"),
    )


def load_game_config(path: Path = DEFAULT_PATH) -> GameConfig:
    resolved = resolve_gitignored(path, cwd=ROOT)
    if not resolved.is_file():
        return GameConfig(source=resolved)
    return parse_game_config(
        resolved.read_text(encoding="utf-8", errors="replace"), resolved
    )
