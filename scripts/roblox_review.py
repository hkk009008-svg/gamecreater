"""Bind a scoped review to actual local candidate and evidence bytes.

Adapted from governance-os compact_pair_loop's exact review pairing and risk
checks. This local tool hashes bytes itself, including evidence, without its
mailbox, model roster, provider dispatch, Git ledger or admission machinery.
It neither authenticates a reviewer nor grants runtime/release acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from game_config import GameConfig, load_game_config

ROOT = Path(__file__).resolve().parent.parent
RISKS = {"ordinary-local", "material-behavior", "high-risk-control"}
LIMITS = [
    "Content and membership checks only; no semantic, runtime or release acceptance.",
    "Non-atomic filesystem reads; two scans reduce but cannot eliminate concurrent changes.",
    "Reviewer and author labels are declarations, not authenticated identities.",
    "Only the supplied snapshot/review pair is checked; no ledger supersession or permission grant.",
]


def exact_keys(value, required: set[str], optional: set[str] = frozenset()) -> None:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise ValueError(f"Expected object keys {sorted(required)}; optional {sorted(optional)}")


def nonblank(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonblank string")
    return value.strip()


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> tuple[dict, bytes]:
    path = safe_absolute(path)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Expected a regular JSON file: {path}")
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid JSON: {value}")))
    if not isinstance(value, dict):
        raise ValueError("JSON document must be an object")
    return value, raw


def relative_path(value) -> str:
    text = nonblank(value, "path")
    if text != value or PureWindowsPath(text).drive or text.startswith(("/", "\\")):
        raise ValueError("Paths must be relative without drives or surrounding whitespace")
    parts = text.replace("\\", "/").split("/")
    if any(p in {"", ".", ".."} or ":" in p or p.endswith((" ", ".")) for p in parts):
        raise ValueError(f"Unsafe relative path: {text}")
    return "/".join(parts)


def safe_absolute(path: Path, *, missing: bool = False) -> Path:
    """Reject links/reparse points in every existing component before resolve."""
    absolute = Path(os.path.abspath(path))
    for component in reversed((absolute, *absolute.parents)):
        try:
            info = component.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Linked/reparse path component refused: {component}")
    return absolute.resolve()


def roots_for(config: GameConfig, harness: Path) -> dict[str, Path]:
    if config.engine_kind != "roblox" or config.project_dir is None:
        raise ValueError("An existing Roblox Project root binding is required")
    roots = {"harness": safe_absolute(harness), "game": safe_absolute(config.project_dir)}
    if any(not path.is_dir() for path in roots.values()):
        raise ValueError("Both bound roots must be directories")
    if roots["harness"] == roots["game"]:
        raise ValueError("Game and harness roots must be separate")
    return roots


def selection(value) -> dict:
    exact_keys(value, {"root", "path"})
    if not isinstance(value["root"], str) or value["root"] not in {"harness", "game"}:
        raise ValueError("Selection root must be harness or game")
    return {"root": value["root"], "path": relative_path(value["path"])}


def selection_path(item: dict, roots: dict[str, Path]) -> Path:
    root = roots[item["root"]]
    path = safe_absolute(root / item["path"])
    if not path.is_relative_to(root):
        raise ValueError("Selection escapes its bound root")
    return path


def validate_scope(value, roots: dict[str, Path]) -> dict:
    exact_keys(value, {"task", "author", "risk", "inputs", "evidence"})
    if not isinstance(value["risk"], str) or value["risk"] not in RISKS:
        raise ValueError("Unknown risk class")
    result = {key: nonblank(value[key], key) for key in ("task", "author", "risk")}
    paths = []
    for role in ("inputs", "evidence"):
        if not isinstance(value[role], list):
            raise ValueError(f"{role} must be an array")
        if not value[role] and (role == "inputs" or value["risk"] != "ordinary-local"):
            raise ValueError(f"{role} must not be empty for this scope")
        result[role] = []
        for raw in value[role]:
            item = selection(raw)
            path = selection_path(item, roots)
            folded = str(path).replace("\\", "/").casefold()
            if any(folded == old or folded.startswith(old + "/") or old.startswith(folded + "/")
                   for old in paths):
                raise ValueError("Duplicate or overlapping selections are not allowed")
            paths.append(folded)
            result[role].append(item)
    return result


def fingerprint(path: Path) -> dict:
    path = safe_absolute(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError(f"File changed before read: {path}")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    safe_absolute(path)
    after = path.stat()
    fields = ("st_size", "st_mtime_ns", "st_ctime_ns", "st_dev", "st_ino")
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise ValueError(f"File changed during read: {path}")
    return {"bytes": after.st_size, "sha256": digest.hexdigest()}


def binding_record(config: GameConfig) -> dict:
    path = safe_absolute(config.source)
    return {"path": str(path), "sha256": fingerprint(path)["sha256"]}


def files_under(path: Path) -> list[Path]:
    """Enumerate all files, refusing unsafe nodes rather than silently skipping."""
    path = safe_absolute(path)
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError(f"Expected file or bounded directory: {path}")
    result = []
    with os.scandir(path) as entries:
        children = sorted((Path(entry.path) for entry in entries), key=str)
    for child in children:
        child = safe_absolute(child)
        if child.is_dir():
            result.extend(files_under(child))
        elif child.is_file():
            result.append(child)
        else:
            raise ValueError(f"Nonregular node refused: {child}")
    return result


def scan(scope: dict, roots: dict[str, Path]) -> list[dict]:
    rows, seen = [], set()
    for role in ("inputs", "evidence"):
        for item in scope[role]:
            members = files_under(selection_path(item, roots))
            if not members:
                raise ValueError(f"Selected directory contains no files: {item}")
            for path in members:
                relative = path.relative_to(roots[item["root"]]).as_posix()
                key = str(path).casefold()
                if key in seen:
                    raise ValueError("Duplicate expanded file membership")
                seen.add(key)
                rows.append({"role": role, "root": item["root"], "path": relative, **fingerprint(path)})
    return sorted(rows, key=lambda row: (row["role"], row["root"], row["path"]))


def validate_output(target: Path, roots: dict[str, Path], scope: dict) -> Path:
    target = safe_absolute(target, missing=True)
    if not target.is_relative_to(roots["harness"]) or not target.name.endswith(".local.json"):
        raise ValueError("Output must be a fresh *.local.json inside the harness")
    if target.is_relative_to(roots["game"]):
        raise ValueError("Output must not be inside the game root")
    if target.exists():
        raise FileExistsError(f"Output already exists: {target}")
    for role in ("inputs", "evidence"):
        for item in scope[role]:
            captured = selection_path(item, roots)
            if target == captured or target.is_relative_to(captured):
                raise ValueError("Output cannot be inside a captured selection")
    return target


def capture(scope: dict, config: GameConfig, target: Path, harness: Path = ROOT) -> dict:
    roots = roots_for(config, harness)
    scope = validate_scope(scope, roots)
    target = validate_output(target, roots, scope)
    binding = binding_record(config)
    rows = scan(scope, roots)
    if scan(scope, roots) != rows or binding_record(config) != binding:
        raise ValueError("Candidate changed during capture; use a fresh stable candidate")
    report = {
        "schemaVersion": 1, "capturedUtc": datetime.now(timezone.utc).isoformat(),
        "binding": binding, "roots": {key: str(path) for key, path in roots.items()},
        "scope": scope, "files": rows, "atomicSnapshot": False, "limits": LIMITS,
    }
    target = validate_output(target, roots, scope)
    target.parent.mkdir(parents=True, exist_ok=True)
    safe_absolute(target.parent)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return report


def check_snapshot(snapshot: dict, config: GameConfig, harness: Path = ROOT) -> dict:
    exact_keys(snapshot, {"schemaVersion", "capturedUtc", "binding", "roots", "scope",
                          "files", "atomicSnapshot", "limits"})
    if type(snapshot["schemaVersion"]) is not int or snapshot["schemaVersion"] != 1:
        raise ValueError("Unknown snapshot schemaVersion")
    if snapshot["atomicSnapshot"] is not False or snapshot["limits"] != LIMITS:
        raise ValueError("Snapshot must retain its explicit limitations")
    timestamp = datetime.fromisoformat(nonblank(snapshot["capturedUtc"], "capturedUtc"))
    if timestamp.tzinfo is None:
        raise ValueError("capturedUtc must have an explicit timezone")
    roots = roots_for(config, harness)
    if snapshot["roots"] != {key: str(path) for key, path in roots.items()}:
        raise ValueError("Bound roots changed")
    if snapshot["binding"] != binding_record(config):
        raise ValueError("Binding path or bytes changed")
    scope = validate_scope(snapshot["scope"], roots)
    if scope != snapshot["scope"]:
        raise ValueError("Snapshot scope must retain its canonical captured values")
    if not isinstance(snapshot["files"], list) or not snapshot["files"]:
        raise ValueError("Snapshot files must be nonempty")
    for row in snapshot["files"]:
        exact_keys(row, {"role", "root", "path", "bytes", "sha256"})
        if type(row["bytes"]) is not int or row["bytes"] < 0:
            raise ValueError("File bytes must be a nonnegative integer")
        if not isinstance(row["sha256"], str) or re.fullmatch("[0-9a-f]{64}", row["sha256"]) is None:
            raise ValueError("File sha256 must be a lowercase SHA-256 digest")
    rows = scan(scope, roots)
    if rows != snapshot["files"]:
        raise ValueError("Content or selected file membership changed")
    if scan(scope, roots) != rows or binding_record(config) != snapshot["binding"]:
        raise ValueError("Candidate changed during check")
    return snapshot


def check_review(review: dict, snapshot: dict, snapshot_bytes: bytes) -> str:
    exact_keys(review, {"schemaVersion", "snapshotSha256", "reviewer", "verdict", "findings", "evidence"},
               {"abuseAnalysis"})
    if type(review["schemaVersion"]) is not int or review["schemaVersion"] != 1:
        raise ValueError("Unknown review schemaVersion")
    digest = review["snapshotSha256"]
    if (not isinstance(digest, str) or re.fullmatch("[0-9a-fA-F]{64}", digest) is None
            or digest.lower() != hashlib.sha256(snapshot_bytes).hexdigest()):
        raise ValueError("Review does not bind the supplied snapshot bytes")
    reviewer = nonblank(review["reviewer"], "reviewer")
    if reviewer.casefold() == nonblank(snapshot["scope"]["author"], "author").casefold():
        raise ValueError("Reviewer must be distinct from the declared author")
    if not isinstance(review["verdict"], str) or review["verdict"] not in {"GO", "NITS", "FAIL"}:
        raise ValueError("Unknown review verdict")
    nonblank(review["findings"], "findings")
    if snapshot["scope"]["risk"] == "high-risk-control":
        nonblank(review.get("abuseAnalysis"), "abuseAnalysis")
    elif "abuseAnalysis" in review and not isinstance(review["abuseAnalysis"], str):
        raise ValueError("abuseAnalysis must be a string when supplied")
    if not isinstance(review["evidence"], list) or not review["evidence"]:
        raise ValueError("Review evidence must be a nonempty array of captured evidence files")
    allowed = {(row["root"], row["path"]) for row in snapshot["files"] if row["role"] == "evidence"}
    seen = set()
    for raw in review["evidence"]:
        item = selection(raw)
        key = (item["root"], item["path"])
        if key not in allowed or key in seen:
            raise ValueError("Review evidence must name unique, exact captured evidence files")
        seen.add(key)
    if review["verdict"] == "FAIL":
        raise ValueError("Reviewer verdict is FAIL")
    return review["verdict"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture_parser = commands.add_parser("capture", help="Capture selected input and evidence bytes")
    capture_parser.add_argument("--scope", type=Path, required=True)
    capture_parser.add_argument("--out", type=Path, required=True)
    check_parser = commands.add_parser("check", help="Recheck content; optionally validate one supplied review")
    check_parser.add_argument("--snapshot", type=Path, required=True)
    check_parser.add_argument("--review", type=Path)
    for command in (capture_parser, check_parser):
        command.add_argument("--binding", type=Path, default=ROOT / "GAME.local.md")
    args = parser.parse_args(argv)
    try:
        config = load_game_config(args.binding)
        if args.command == "capture":
            scope, _ = read_json(args.scope)
            report = capture(scope, config, args.out, ROOT)
            print(f"CAPTURED: {len(report['files'])} files; {args.out.resolve()}")
        else:
            snapshot, raw = read_json(args.snapshot)
            check_snapshot(snapshot, config, ROOT)
            if args.review:
                review, _ = read_json(args.review)
                verdict = check_review(review, snapshot, raw)
                print(f"CONTENT MATCH; SCOPED REVIEW {verdict}: supplied pair and declared reviewer checked.")
            else:
                print("CONTENT MATCH only. No review or approval was supplied.")
        print("Content checks are non-atomic. Labels are unauthenticated; no runtime acceptance or authority is granted.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print(f"REVIEW CHECK REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
