"""Inspect declared visual evidence and assemble an offline review packet.

This tool checks bytes, metadata and comparison eligibility. It does not capture
Studio, measure performance, authenticate provenance or decide visual quality.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import sys
import warnings

from PIL import Image

from roblox_review import exact_keys, safe_absolute

ROOT = Path(__file__).resolve().parent.parent
PACKET_ROOT = ROOT / "team" / "visual-packets"
MAX_MANIFEST = 2 * 1024 * 1024
MAX_MEDIA = 128 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
MAX_PIXELS = 40_000_000
CONTEXT_KEYS = {
    "map", "subject", "phase", "lighting", "quality", "device", "randomState",
    "camera", "fov", "viewport", "input", "captureMode", "sequenceTime",
}
REQUIRED_CONTEXT = CONTEXT_KEYS - {"sequenceTime"}
MODES = {"native-still", "native-video", "studio-screenshot", "stepped-video", "unknown"}
INPUTS = {"native", "scripted", "none", "unknown"}
LIMITS = [
    "Metadata eligibility only; no visual-quality judgment, user acceptance or release approval.",
    "Build, device, capture mode and control descriptions are declarations, not authenticated provenance.",
    "PNG/JPEG pixels are decoded; MP4 is signature-checked only, without decoding or frame synchronization.",
    "No image difference, FPS, physical-device performance or native execution is measured.",
    "Non-atomic local reads detect common concurrent changes but cannot eliminate filesystem races.",
]


def text(value, label, *, nullable=False):
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 8000:
        raise ValueError(f"{label} must be a nonblank string of at most 8000 characters")
    return value


def array(value, label, *, minimum=0, maximum=100):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} must contain {minimum} to {maximum} items")
    return value


def strings(value, label, *, minimum=0, unique=False):
    result = [text(item, label) for item in array(value, label, minimum=minimum)]
    if unique and len(set(result)) != len(result):
        raise ValueError(f"{label} must contain unique values")
    return result


def digest(value, label, *, nullable=False):
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", value):
        raise ValueError(f"{label} must be a SHA-256 digest")
    return value.lower()


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def number(value, label, *, minimum=0, positive=False):
    if not finite_number(value):
        raise ValueError(f"{label} must be a finite number")
    if value < minimum or (positive and value == minimum):
        raise ValueError(f"{label} is out of range")
    return value


def local_path(value, base):
    raw = text(str(value), "local path")
    if "\x00" in raw or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raise ValueError("Only local filesystem paths are supported")
    if raw.startswith(("\\\\", "//")):
        raise ValueError("Network shares and device namespaces are not supported")
    windows = PureWindowsPath(raw)
    if windows.drive and not windows.root:
        raise ValueError("Drive-relative paths are ambiguous and not supported")
    # Reject alternate streams and ambiguous Windows component aliases.
    for part in windows.parts[1:] if windows.anchor else windows.parts:
        if ":" in part or (part not in {".", ".."} and part.endswith((" ", "."))):
            raise ValueError(f"Unsafe path component: {part}")
    path = Path(raw)
    return path if path.is_absolute() else Path(base) / path


def read_bytes(path, limit):
    path = safe_absolute(local_path(path, Path.cwd()))
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError(f"Expected regular file no larger than {limit} bytes: {path}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError(f"File changed before read: {path}")
        raw = stream.read(limit + 1)
    after = safe_absolute(path).stat()
    fields = ("st_size", "st_mtime_ns", "st_ctime_ns", "st_dev", "st_ino")
    if len(raw) > limit or len(raw) != before.st_size or any(
        getattr(before, field) != getattr(after, field) for field in fields
    ):
        raise ValueError(f"File changed during read: {path}")
    return path, raw


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_manifest(path):
    path, raw = read_bytes(path, MAX_MANIFEST)
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                       parse_constant=lambda item: (_ for _ in ()).throw(
                           ValueError(f"Invalid JSON constant: {item}")))
    return path, raw, validate_manifest(value)


def normalize_context(value):
    exact_keys(value, set(), CONTEXT_KEYS)
    result = dict.fromkeys(CONTEXT_KEYS)
    result.update(input="unknown", captureMode="unknown")
    result.update(value)
    for key in {"map", "subject", "phase", "lighting", "quality", "device", "randomState"}:
        text(result[key], f"context.{key}", nullable=True)
    if result["input"] not in INPUTS or result["captureMode"] not in MODES:
        raise ValueError("Unknown input or captureMode")
    if result["camera"] is not None:
        array(result["camera"], "camera", minimum=12, maximum=12)
        for item in result["camera"]:
            if not finite_number(item):
                raise ValueError("camera must contain twelve finite numbers")
    if result["viewport"] is not None:
        array(result["viewport"], "viewport", minimum=2, maximum=2)
        if any(type(item) is not int or item < 1 or item > 65536 for item in result["viewport"]):
            raise ValueError("viewport must contain positive bounded integers")
    if result["fov"] is not None:
        number(result["fov"], "fov", positive=True)
        if result["fov"] > 180:
            raise ValueError("fov must be at most 180")
    if result["sequenceTime"] is not None:
        number(result["sequenceTime"], "sequenceTime")
    return result


def normalize_eligibility(value):
    exact_keys(value, set(), {"subjectVisible", "unscaled", "controls", "repeat"})
    result = {"subjectVisible": None, "unscaled": None, "controls": [], "repeat": None}
    result.update(value)
    for key in ("subjectVisible", "unscaled"):
        if result[key] is not None and type(result[key]) is not bool:
            raise ValueError(f"{key} must be boolean or null")
    text(result["repeat"], "repeat", nullable=True)
    layers = set()
    for item in array(result["controls"], "controls"):
        exact_keys(item, {"layer", "visible", "evidence"})
        text(item["layer"], "control layer")
        if item["layer"] in layers:
            raise ValueError("Duplicate control layer")
        layers.add(item["layer"])
        if item["visible"] is not None and type(item["visible"]) is not bool:
            raise ValueError("control.visible must be boolean or null")
        text(item["evidence"], "control evidence", nullable=True)
    return result


def validate_manifest(value):
    exact_keys(value, {"schemaVersion", "title", "question", "direction", "captures",
                       "comparisons", "coverage", "decisions"})
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise ValueError("Unsupported schemaVersion")
    result = deepcopy(value)
    for key in ("title", "question"):
        text(result[key], key)
    direction = result["direction"]
    exact_keys(direction, {"promise", "rules", "avoid", "preserve"})
    text(direction["promise"], "direction.promise")
    for key in ("rules", "avoid", "preserve"):
        strings(direction[key], f"direction.{key}")
    capture_ids = set()
    for capture in array(result["captures"], "captures", minimum=1):
        exact_keys(capture, {"id", "label", "media", "build", "context", "eligibility", "notes"})
        text(capture["id"], "capture id")
        text(capture["label"], "capture label")
        if capture["id"] in capture_ids:
            raise ValueError("Duplicate capture id")
        capture_ids.add(capture["id"])
        exact_keys(capture["media"], {"path", "sha256"})
        text(capture["media"]["path"], "media.path")
        capture["media"]["sha256"] = digest(capture["media"]["sha256"], "media.sha256")
        exact_keys(capture["build"], {"id", "sha256"})
        text(capture["build"]["id"], "build.id", nullable=True)
        capture["build"]["sha256"] = digest(capture["build"]["sha256"], "build.sha256", nullable=True)
        capture["context"] = normalize_context(capture["context"])
        capture["eligibility"] = normalize_eligibility(capture["eligibility"])
        strings(capture["notes"], "notes")
    for capture in result["captures"]:
        refs = [capture["eligibility"]["repeat"]] + [
            item["evidence"] for item in capture["eligibility"]["controls"]]
        if any(item is not None and item not in capture_ids for item in refs):
            raise ValueError("Capture evidence/repeat references an unknown capture")
    comparison_ids = set()
    for item in array(result["comparisons"], "comparisons"):
        exact_keys(item, {"id", "title", "question", "baseline", "candidate", "purpose",
                          "changedFactors", "requiredLayers"})
        for key in ("id", "title", "question", "baseline", "candidate"):
            text(item[key], f"comparison.{key}")
        if item["id"] in comparison_ids:
            raise ValueError("Duplicate comparison id")
        comparison_ids.add(item["id"])
        if item["baseline"] not in capture_ids or item["candidate"] not in capture_ids:
            raise ValueError("Comparison references an unknown capture")
        if item["baseline"] == item["candidate"]:
            raise ValueError("Comparison requires two different captures")
        if item["purpose"] not in {"aesthetic", "pixel", "motion"}:
            raise ValueError("Unknown comparison purpose")
        changed = strings(item["changedFactors"], "changedFactors", unique=True)
        if len(changed) > 1 or any(key not in CONTEXT_KEYS for key in changed):
            raise ValueError("changedFactors permits at most one known context key")
        strings(item["requiredLayers"], "requiredLayers", minimum=1, unique=True)
    for row in array(result["coverage"], "coverage"):
        exact_keys(row, {"label", "captureIds", "note"})
        text(row["label"], "coverage label")
        text(row["note"], "coverage note")
        ids = strings(row["captureIds"], "coverage captureIds", unique=True)
        if any(item not in capture_ids for item in ids):
            raise ValueError("Coverage references an unknown capture")
    decisions = result["decisions"]
    exact_keys(decisions, {"status", "userVerdict", "nextExperiment"})
    if decisions["status"] not in {"pending", "keep", "revise", "reject"}:
        raise ValueError("Unknown decisions.status")
    text(decisions["userVerdict"], "userVerdict", nullable=True)
    text(decisions["nextExperiment"], "nextExperiment")
    return result


def inspect_media(raw):
    if len(raw) >= 16 and raw[4:8] == b"ftyp":
        box_size = int.from_bytes(raw[:4], "big")
        if box_size < 16 or box_size > len(raw) or box_size % 4:
            raise ValueError("Malformed MP4 file-type box")
        brands = {raw[8:12], *(raw[offset:offset + 4] for offset in range(16, box_size, 4))}
        video_brands = {b"isom", b"iso2", b"iso3", b"iso4", b"iso5", b"iso6",
                        b"mp41", b"mp42", b"avc1", b"M4V ", b"dash"}
        still_brands = {b"avif", b"avis", b"mif1", b"msf1", b"heic", b"heix",
                        b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs"}
        if brands & still_brands or not brands & video_brands:
            raise ValueError("ISO-BMFF signature is not a supported MP4 video container")
        return {"kind": "video", "format": "MP4", "width": None, "height": None}, "mp4"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as picture:
                if picture.format not in {"PNG", "JPEG"}:
                    raise ValueError("Only PNG, JPEG and MP4 media are supported")
                if picture.width * picture.height > MAX_PIXELS:
                    raise ValueError("Decoded image exceeds 40 million pixels")
                picture.load()
                result = {"kind": "image", "format": picture.format,
                          "width": picture.width, "height": picture.height}
        return result, "png" if result["format"] == "PNG" else "jpg"
    except (OSError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError(f"Media cannot be fully decoded as PNG/JPEG: {exc}") from exc


def known(value):
    return value is not None and value != "unknown"


def media_context_issues(capture):
    problems = []
    mode = capture["context"]["captureMode"]
    expected = {"native-still": "image", "studio-screenshot": "image",
                "native-video": "video", "stepped-video": "video"}.get(mode)
    if expected and expected != capture["kind"]:
        problems.append("media kind is incompatible with declared captureMode")
    if capture["kind"] == "image" and capture["context"]["viewport"] != [
        capture["width"], capture["height"]
    ]:
        problems.append("decoded dimensions do not match declared viewport")
    return problems


def side_issues(capture, layers, captures):
    problems = []
    label = capture["id"]
    for key in sorted(REQUIRED_CONTEXT):
        if not known(capture["context"][key]):
            problems.append(f"{label}: unknown {key}")
    if not capture["build"]["id"] or not capture["build"]["sha256"]:
        problems.append(f"{label}: build id and SHA-256 are required")
    if capture["eligibility"]["subjectVisible"] is not True:
        problems.append(f"{label}: subject visibility is not confirmed")
    problems += [f"{label}: {problem}" for problem in media_context_issues(capture)]
    controls = {item["layer"]: item for item in capture["eligibility"]["controls"]}
    for layer in layers:
        control = controls.get(layer)
        if not control or control["visible"] is not True or not control["evidence"]:
            problems.append(f"{label}: {layer} visibility control is missing or not passing")
            continue
        evidence = captures[control["evidence"]]
        problems += [f"{label}: {layer} control evidence {problem}"
                     for problem in media_context_issues(evidence)]
        for key in ("captureMode", "viewport", "quality"):
            if not known(evidence["context"][key]) or evidence["context"][key] != capture["context"][key]:
                problems.append(f"{label}: {layer} control evidence has incompatible {key}")
    return problems


def compare(item, captures, paths):
    result = deepcopy(item)
    left, right = captures[item["baseline"]], captures[item["candidate"]]
    issues = side_issues(left, item["requiredLayers"], captures)
    issues += side_issues(right, item["requiredLayers"], captures)
    for key in item["changedFactors"]:
        for capture in (left, right):
            if not known(capture["context"][key]):
                issues.append(f"{capture['id']}: declared changed factor {key} is unknown")
    differences = []
    for key in sorted(CONTEXT_KEYS):
        a, b = left["context"][key], right["context"][key]
        if a != b:
            declared = key in item["changedFactors"]
            differences.append({"field": key, "baseline": a, "candidate": b, "declared": declared})
            if not declared:
                issues.append(f"Undeclared context difference: {key}")
    if left["kind"] != right["kind"]:
        issues.append("Media kinds differ")
    if item["purpose"] == "pixel":
        for capture in (left, right):
            label = capture["id"]
            if capture["format"] != "PNG" or capture["eligibility"]["unscaled"] is not True:
                issues.append(f"{label}: pixel review requires decoded PNG and unscaled=true")
            repeat_id = capture["eligibility"]["repeat"]
            if not repeat_id or repeat_id == label:
                issues.append(f"{label}: a distinct repeat capture is required")
                continue
            repeat = captures[repeat_id]
            if paths[repeat_id] == paths[label]:
                issues.append(f"{label}: repeat reuses the original media path")
            if repeat["build"] != capture["build"] or repeat["context"] != capture["context"]:
                issues.append(f"{label}: repeat must use the same build and context")
            if repeat["format"] != "PNG" or repeat["eligibility"]["unscaled"] is not True:
                issues.append(f"{label}: repeat requires PNG and unscaled=true")
            issues += [f"{label} repeat: {problem}" for problem in side_issues(
                repeat, item["requiredLayers"], captures)]
    if item["purpose"] == "motion":
        for capture in (left, right):
            if capture["format"] != "MP4" or capture["context"]["captureMode"] != "native-video" \
                    or capture["context"]["input"] != "native":
                issues.append(f"{capture['id']}: native motion requires MP4, native-video and native input")
    result.update(comparable=not issues, issues=issues, differences=differences)
    return result


def _inspect_manifest(path):
    manifest_path, raw, manifest = read_manifest(path)
    assets, captures, paths = {}, {}, {}
    total = 0
    for declaration in manifest["captures"]:
        path, media = read_bytes(local_path(declaration["media"]["path"], manifest_path.parent), MAX_MEDIA)
        actual = hashlib.sha256(media).hexdigest()
        if actual != declaration["media"]["sha256"]:
            raise ValueError(f"{declaration['id']}: media SHA-256 mismatch")
        info, extension = inspect_media(media)
        media_path = f"media/{actual}.{extension}"
        if media_path not in assets:
            total += len(media)
            if total > MAX_TOTAL:
                raise ValueError("Aggregate media exceeds 512 MiB")
            assets[media_path] = media
        record = {key: deepcopy(declaration[key]) for key in
                  ("id", "label", "build", "context", "eligibility", "notes")}
        record.update(info, sha256=actual, bytes=len(media), mediaPath=media_path)
        captures[record["id"]] = record
        paths[record["id"]] = path
    comparisons = [compare(item, captures, paths) for item in manifest["comparisons"]]
    missing = [row["label"] for row in manifest["coverage"] if not row["captureIds"]]
    ready = bool(comparisons) and all(item["comparable"] for item in comparisons) and not missing
    report = {
        "schemaVersion": 1, "execution": "inspected",
        "manifestSha256": hashlib.sha256(raw).hexdigest(),
        "status": "ready-for-review" if ready else "needs-evidence",
        "errors": [], "limits": LIMITS.copy(), "captures": list(captures.values()),
        "comparisons": comparisons, "coverage": manifest["coverage"],
        "missingCoverage": missing, "decisions": manifest["decisions"],
    }
    return manifest, report, assets, raw


def inspect_manifest(path):
    """Return normalized declarations, eligibility report and immutable media bytes."""
    manifest, report, assets, _ = _inspect_manifest(path)
    return manifest, report, assets


def fresh_path(path, root):
    output = safe_absolute(path, missing=True)
    bound = safe_absolute(root, missing=True)
    if not output.is_relative_to(bound) or output == bound:
        raise ValueError(f"Output must be inside {bound}")
    if output.exists():
        raise ValueError(f"Output already exists; use a fresh path: {output}")
    return output


def build_packet(manifest_path, output_path):
    output = fresh_path(local_path(output_path, Path.cwd()), PACKET_ROOT)
    manifest, report, assets, original_manifest = _inspect_manifest(manifest_path)
    manifest_source = safe_absolute(Path(manifest_path))
    inputs = [manifest_source] + [
        safe_absolute(local_path(item["media"]["path"], manifest_source.parent))
        for item in manifest["captures"]]
    if any(path == output or path.is_relative_to(output) for path in inputs):
        raise ValueError("Output directory overlaps an input")
    from roblox_visual_html import render_packet
    html = render_packet(manifest, report)
    # Inspect before creating anything. Exclusive writes never replace prior evidence.
    output.parent.mkdir(parents=True, exist_ok=True)
    fresh_path(output, PACKET_ROOT)
    output.mkdir()
    safe_absolute(output)
    (output / "media").mkdir()
    for relative, raw in assets.items():
        with (safe_absolute(output / "media") / Path(relative).name).open("xb") as stream:
            stream.write(raw)
    for name, raw in {
        "manifest.json": original_manifest,
        "report.json": json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"),
        "index.html": html.encode("utf-8"),
    }.items():
        with (safe_absolute(output) / name).open("xb") as stream:
            stream.write(raw)
    return report


def init_manifest(media_paths, output_path, title="Visual review experiment"):
    output = fresh_path(local_path(output_path, Path.cwd()), ROOT)
    if not output.name.endswith(".local.json"):
        raise ValueError("Manifest output must end in .local.json")
    array(media_paths, "media paths", minimum=1)
    captures = []
    total = 0
    for index, media_path in enumerate(media_paths, 1):
        path, raw = read_bytes(local_path(media_path, Path.cwd()), MAX_MEDIA)
        inspect_media(raw)
        total += len(raw)
        if total > MAX_TOTAL:
            raise ValueError("Aggregate media exceeds 512 MiB")
        captures.append({
            "id": f"capture-{index}", "label": path.name,
            "media": {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()},
            "build": {"id": None, "sha256": None}, "context": {},
            "eligibility": {"controls": [{"layer": "world", "visible": None, "evidence": None}]},
            "notes": ["Complete metadata from actual capture evidence before comparing."],
        })
    value = {
        "schemaVersion": 1, "title": title,
        "question": "What specific visual change should this experiment evaluate?",
        "direction": {"promise": "Describe the intended player experience.",
                      "rules": [], "avoid": [], "preserve": []},
        "captures": captures, "comparisons": [], "coverage": [],
        "decisions": {"status": "pending", "userVerdict": None,
                      "nextExperiment": "Record build, capture settings and visibility-control evidence."},
    }
    if len(captures) >= 2:
        value["comparisons"].append({
            "id": "comparison-1", "title": "Baseline and candidate",
            "question": value["question"], "baseline": "capture-1", "candidate": "capture-2",
            "purpose": "aesthetic", "changedFactors": [], "requiredLayers": ["world"],
        })
    value = validate_manifest(value)
    encoded = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_MANIFEST:
        raise ValueError("Generated manifest exceeds 2 MiB")
    output.parent.mkdir(parents=True, exist_ok=True)
    fresh_path(output, ROOT)
    with output.open("xb") as stream:
        stream.write(encoded)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "build"):
        command = sub.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--require-comparable", action="store_true")
        if name == "build":
            command.add_argument("--out", type=Path, required=True)
    initialize = sub.add_parser("init")
    initialize.add_argument("--media", type=Path, action="append", required=True)
    initialize.add_argument("--out", type=Path, required=True)
    initialize.add_argument("--title", default="Visual review experiment")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            value = init_manifest(args.media, args.out, args.title)
            print(json.dumps({"status": "initialized", "manifest": str(args.out),
                              "captureCount": len(value["captures"]),
                              "limits": ["Unknown settings must be completed from actual capture evidence."]}))
            return 0
        report = build_packet(args.manifest, args.out) if args.command == "build" else inspect_manifest(args.manifest)[1]
        # ASCII JSON escapes keep redirected output valid on Windows legacy consoles.
        print(json.dumps(report, indent=2))
        return 2 if args.require_comparable and report["status"] != "ready-for-review" else 0
    except (ValueError, OSError, UnicodeError, TypeError, RecursionError) as exc:
        print(json.dumps({"schemaVersion": 1, "execution": "failed",
                          "status": "needs-evidence", "errors": [str(exc)], "limits": LIMITS},
                         ensure_ascii=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
