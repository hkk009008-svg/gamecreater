"""Read-only Roblox team status, setup checks and project knowledge inventory.

No Studio control, game execution, downloads or account operations. Inventory
writes only a fresh *.local.json file inside this control repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from game_config import GameConfig, load_game_config

ROOT = Path(__file__).resolve().parent.parent
TEXT_INPUTS = {".lua", ".luau", ".py", ".ps1", ".json", ".md", ".toml", ".txt", ".yaml", ".yml"}
TEAM_FILES = (
    "team/NOW.md", "docs/roblox-team.md", "docs/skill-routing.md",
    "templates/ROBLOX-TASK.template.md", "templates/ROBLOX-HANDOFF.template.md",
    "skills/roblox/build-roblox-game/SKILL.md",
    "docs/roblox-governance.md", "team/DECISIONS.md",
    "scripts/roblox_review.py",
    "templates/ROBLOX-REVIEW-SCOPE.template.json",
    "templates/ROBLOX-REVIEW.template.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def manifest_paths(node, prefix: str = "") -> list[tuple[str, str]]:
    """Read actual Rojo mappings; do not import or execute the mapped source."""
    found = []
    if isinstance(node, dict):
        if isinstance(node.get("$path"), str):
            found.append((prefix, node["$path"]))
        for name, child in node.items():
            if not name.startswith("$"):
                found.extend(manifest_paths(child, f"{prefix}/{name}".strip("/")))
    return found


def check_setup(config: GameConfig, harness: Path = ROOT) -> list[str]:
    problems = []
    if config.engine_kind != "roblox":
        problems.append(f"Active Engine must be Roblox Studio, got {config.engine_kind}")
    for label, path, kind in (
        ("Working root", config.working_root, "dir"),
        ("Project root", config.project_root, "dir"),
        ("Project manifest", config.project_file, "file"),
        ("Game NOW.md", config.now, "file"),
        ("Lessons inbox", config.lessons, "file"),
        ("Team NOW.md", config.team_now, "file"),
    ):
        if path is None or not (path.is_dir() if kind == "dir" else path.is_file()):
            problems.append(f"{label} is missing: {path or 'UNSET'}")
    if config.project_root and config.project_root.resolve() == harness.resolve():
        problems.append("Game source root must be separate from the control repository")
    if not config.integration_owner:
        problems.append("Integration owner is unassigned")
    for relative in TEAM_FILES:
        if not (harness / relative).is_file():
            problems.append(f"Team file missing: {relative}")
    manifest, root = config.project_file, config.project_dir
    if manifest and manifest.is_file() and root:
        if not manifest.resolve().is_relative_to(root.resolve()):
            problems.append("Project manifest escapes the game Project root")
        elif manifest.suffix.lower() == ".json":
            try:
                data = json.loads(manifest.read_text(encoding="utf-8-sig"))
                if not isinstance(data, dict) or not isinstance(data.get("tree"), dict):
                    raise ValueError("Rojo manifest has no tree object")
                for instance, raw in manifest_paths(data["tree"]):
                    target = (manifest.parent / raw).resolve()
                    if not target.is_relative_to(root.resolve()):
                        problems.append(f"Mapping escapes game root: {instance} -> {raw}")
                    elif not target.exists():
                        problems.append(f"Mapped source missing: {instance} -> {raw}")
            except (OSError, ValueError) as exc:
                problems.append(f"Cannot inspect project manifest: {exc}")
    return problems


def workflow_input(relative: Path) -> bool:
    parts = relative.parts
    if any(part.casefold() in {"_vendor", "vendor", "node_modules", "site-packages", "__pycache__"} for part in parts):
        return False
    in_scope = len(parts) == 1 or parts[0] in {"src", "scripts", "assets"}
    in_scope = in_scope or relative.as_posix().startswith("tools/paper_assets/")
    return in_scope and relative.suffix.lower() in TEXT_INPUTS


def inventory_project(config: GameConfig) -> dict:
    root = config.project_dir
    if config.engine_kind != "roblox" or root is None or not root.is_dir():
        raise ValueError("Inventory requires an existing Roblox Project root")
    root = root.resolve()
    report = {
        "schemaVersion": 1, "startedUtc": utc_now(), "project": config.name,
        "root": str(root), "binding": str(config.source),
        "atomicSnapshot": False,
        "limits": [
            "File inventory and selected fingerprints; not semantic review or gameplay acceptance.",
            "Active integration may change files; revalidate against the exact saved-build receipt.",
            "No content hashes for build/evidence/backup binaries or vendored tool libraries.",
        ],
        "files": [], "errors": [], "skipped": [], "sourceMappings": [],
    }
    categories, evidence = Counter(), Counter()

    def walk_error(exc):
        report["errors"].append(str(exc))

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        retained = []
        for name in sorted(dirs):
            candidate = Path(directory) / name
            # Do not traverse linked/reparse directories or Git internals.
            if name == ".git" or candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
                report["skipped"].append(str(candidate.relative_to(root)))
            else:
                retained.append(name)
        dirs[:] = retained
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(root)
            try:
                if path.is_symlink():
                    report["skipped"].append(relative.as_posix())
                    continue
                before = path.stat()
                category = relative.parts[0] if len(relative.parts) > 1 else "root-docs-config"
                record = {"path": relative.as_posix(), "bytes": before.st_size,
                          "mtimeNs": before.st_mtime_ns, "category": category}
                if workflow_input(relative):
                    with path.open("rb") as stream:
                        record["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
                    after = path.stat()
                    record["changedDuringRead"] = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
                    if record["changedDuringRead"]:
                        report["errors"].append(f"Changed during fingerprint: {relative}")
                report["files"].append(record)
                categories[category] += 1
                if len(relative.parts) > 1 and relative.parts[0] == "evidence":
                    evidence[relative.parts[1]] += 1
            except OSError as exc:
                report["errors"].append(f"{relative}: {exc}")
    manifest = config.project_file
    if manifest and manifest.suffix.lower() == ".json":
        try:
            data = json.loads(manifest.read_text(encoding="utf-8-sig"))
            report["sourceMappings"] = [
                {"instance": instance, "path": raw}
                for instance, raw in manifest_paths(data["tree"])
            ]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            report["errors"].append(f"Manifest: {exc}")
    report.update({"finishedUtc": utc_now(), "fileCount": len(report["files"]),
                   "fingerprintCount": sum("sha256" in row for row in report["files"]),
                   "categories": dict(sorted(categories.items())),
                   "evidenceDirectories": dict(sorted(evidence.items())),
                   "status": "partial" if report["errors"] else "indexed"})
    return report


def write_inventory(report: dict, target: Path, harness: Path = ROOT) -> None:
    target = target.resolve()
    if not target.is_relative_to(harness.resolve()) or not target.name.endswith(".local.json"):
        raise ValueError("Inventory output must be a fresh *.local.json inside the control repository")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "check", "inventory"))
    parser.add_argument("--binding", type=Path, default=ROOT / "GAME.local.md")
    parser.add_argument("--out", type=Path, help="fresh ignored inventory path inside this repository")
    args = parser.parse_args(argv)
    config = load_game_config(args.binding)
    if args.command == "status":
        print(f"Roblox team | {config.name or 'UNBOUND'} | engine={config.engine_kind}")
        print(f"Source: {config.project_dir or 'UNSET'}")
        print(f"Manifest: {config.project_file or 'UNSET'}")
        print(f"Game state: {config.now or 'UNSET'}")
        print(f"Team state: {config.team_now or 'UNSET'}")
        print(f"Integration owner: {config.integration_owner or 'UNASSIGNED'}")
        print("Studio identity/Play state: NOT QUERIED. Enumerate live instances before Studio work.")
        print("Roles: lead/integrator; server gameplay; client/UI; world/art/audio; QA/release")
        return 0
    problems = check_setup(config)
    if problems:
        for problem in problems:
            print(f"SETUP ISSUE: {problem}", file=sys.stderr)
        return 1
    if args.command == "check":
        print("Team setup checks passed: binding, roots, manifest mappings, owner and team files.")
        print("This checks local setup only; no Studio, game build or gameplay test ran.")
        return 0
    target = args.out or ROOT / "team" / ("inventory-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".local.json")
    try:
        report = inventory_project(config)
        write_inventory(report, target)
    except (OSError, ValueError) as exc:
        print(f"Inventory refused: {exc}", file=sys.stderr)
        return 1
    print(f"Inventory {report['status']}: {report['fileCount']} files, "
          f"{report['fingerprintCount']} workflow fingerprints, "
          f"{len(report['errors'])} read/change errors; {target.resolve()}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, "reconfigure"):
            output.reconfigure(errors="backslashreplace")
    sys.exit(main())
