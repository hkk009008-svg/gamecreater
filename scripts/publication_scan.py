"""Pure, redacted content scan for explicitly collected local Git sources.

The collector owns Git selection and payload bounds. This layer reuses the
existing scrub rule loader, text decoder and line cap, records coverage gaps,
and retains findings. It neither grants publication authority nor suppresses
findings that a later reviewer classifies as fixtures or public baseline.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import scrub_check


MAX_TERM_BYTES = 1024 * 1024
MAX_LINE_BUDGET = 1024 * 1024
OBJECT_KINDS = {"blob", "commit", "tag"}
PATH_MODES = {"100644", "100755", "120000", "160000", "040000"}
OID_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class _ScanError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _digest(value: str | bytes) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8", "surrogatepass")
    return hashlib.sha256(data).hexdigest()


def _identity(value: dict) -> str:
    return _digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


def _oid(value: object) -> bool:
    return isinstance(value, str) and OID_RE.fullmatch(value) is not None


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and "\x00" not in value


def _load_rules(term_paths: list[Path]) -> tuple[list[dict], list[dict]]:
    if not isinstance(term_paths, list) or not term_paths:
        raise _ScanError("terms-missing", "At least one explicit term file is required")
    rules: dict[str, dict] = {}
    files = []
    seen = set()
    for supplied in term_paths:
        try:
            path = Path(supplied).resolve(strict=True)
            if not path.is_file():
                raise _ScanError("terms-unreadable", "Term input is not a regular file")
            key = str(path)
            if key in seen:
                raise _ScanError("terms-duplicate", "A term file was selected more than once")
            seen.add(key)
            with path.open("rb") as stream:
                data = stream.read(MAX_TERM_BYTES + 1)
            if len(data) > MAX_TERM_BYTES:
                raise _ScanError("terms-too-large", "Term input exceeds the per-file byte limit")
            text = data.decode("utf-8-sig", "strict")
        except _ScanError:
            raise
        except (OSError, UnicodeError, TypeError, ValueError):
            raise _ScanError("terms-unreadable", "An explicitly selected term file cannot be read as UTF-8") from None
        file_id = _digest(data)
        loaded = 0
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip() or line.strip().startswith("#"):
                continue
            if line.strip() == "re:":
                raise _ScanError("terms-empty-expression", "An explicit regex rule has no expression")
            try:
                compiled = scrub_check.load_terms([line])
            except (re.error, ValueError, TypeError):
                raise _ScanError("terms-invalid-expression", "An explicit regex rule could not be compiled") from None
            if len(compiled) != 1:
                raise _ScanError("terms-invalid-rule", "A non-comment rule did not produce one pattern")
            pattern = compiled[0]
            rule_id = _identity({"pattern": pattern.pattern, "flags": pattern.flags})
            provenance = {"termFileSha256": file_id, "line": number}
            if rule_id not in rules:
                rules[rule_id] = {"ruleId": rule_id, "pattern": pattern, "origins": []}
            rules[rule_id]["origins"].append(provenance)
            loaded += 1
        if loaded == 0:
            raise _ScanError("terms-empty-tier", "An explicitly selected term tier contains no rules")
        files.append({"path": str(path), "sha256": file_id, "bytes": len(data), "ruleEntries": loaded})
    return sorted(rules.values(), key=lambda row: row["ruleId"]), files


def _validated(sources: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    if not isinstance(sources, dict):
        raise _ScanError("sources-invalid", "Collected sources must be an object")
    arrays = []
    for key in ("objects", "paths", "refs", "coverageGaps"):
        value = sources.get(key)
        if not isinstance(value, list):
            raise _ScanError("sources-invalid", f"Collected {key} must be an array")
        arrays.append(value)
    objects, paths, refs, gaps = arrays
    if not objects and not paths and not refs:
        raise _ScanError("sources-empty", "No collected content or identities were selected")
    seen = set()
    for row in objects:
        if (not isinstance(row, dict) or not _oid(row.get("oid"))
                or row.get("kind") not in OBJECT_KINDS or not isinstance(row.get("data"), bytes)):
            raise _ScanError("object-invalid", "A Git payload has invalid identity, kind or bytes")
        if row["oid"] in seen:
            raise _ScanError("object-duplicate", "A Git object identity was collected more than once")
        seen.add(row["oid"])
    object_kinds = {row["oid"]: row["kind"] for row in objects}
    seen = set()
    for row in paths:
        if (not isinstance(row, dict) or not _text(row.get("path")) or not _oid(row.get("oid"))
                or row.get("mode") not in PATH_MODES
                or ("tree" in row and not _oid(row["tree"]))):
            raise _ScanError("path-invalid", "A Git path has invalid identity, mode or name")
        key = (row.get("tree", ""), row["path"], row["oid"], row["mode"])
        if key in seen:
            raise _ScanError("path-duplicate", "A Git path identity was collected more than once")
        seen.add(key)
        if row["mode"] in {"100644", "100755", "120000"} and object_kinds.get(row["oid"]) != "blob":
            raise _ScanError("path-payload-missing", "An ordinary Git path has no collected blob payload")
    seen = set()
    for row in refs:
        if not isinstance(row, dict) or not _text(row.get("name")) or not _oid(row.get("oid")):
            raise _ScanError("ref-invalid", "A Git ref has invalid name or target identity")
        if row["name"] in seen:
            raise _ScanError("ref-duplicate", "A Git ref name was collected more than once")
        seen.add(row["name"])
    for row in gaps:
        if not isinstance(row, dict):
            raise _ScanError("gap-invalid", "A declared coverage gap is not an object")
        try:
            json.dumps(row, ensure_ascii=True, allow_nan=False)
        except (ValueError, TypeError):
            raise _ScanError("gap-invalid", "A declared coverage gap cannot be recorded") from None
    for key in ("mode", "selection", "sourceIdentity"):
        if key in sources:
            try:
                json.dumps(sources[key], ensure_ascii=True, allow_nan=False)
            except (ValueError, TypeError):
                raise _ScanError("provenance-invalid", "Collected provenance cannot be recorded") from None
    return objects, paths, refs, gaps


def _strict_decode(data: bytes) -> tuple[str | None, str | None]:
    """Keep the legacy decoding behavior while exposing replacement/skip gaps."""
    if data[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"):
        encoding = "utf-32"
    elif data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"
    decoded = scrub_check.decode_text(data)
    if decoded is None:
        return None, "binary-skipped"
    if encoding == "utf-8-sig" and data.startswith(b"\xef\xbb\xbf"):
        # The legacy decoder keeps UTF-8 BOM while its UTF-16/32 decoders strip
        # their BOMs. Normalize here so an anchored policy is not evaded solely
        # by this supported encoding wrapper, including replacement-text scans.
        decoded = decoded[1:]
    try:
        data.decode(encoding, "strict")
    except UnicodeError:
        return decoded, "invalid-text-encoding"
    if encoding == "utf-8-sig" and b"\x00" in data:
        return decoded, "binary-nul-outside-decoder-prefix"
    return decoded, None


def scan_sources(sources: dict, term_paths: list[Path], *,
                 max_line_chars: int = scrub_check.MAX_LINE_CHARS) -> dict:
    """Scan a collector snapshot without repository, network or output writes.

    INCOMPLETE has precedence over FINDINGS: findings are still retained. A
    reviewer disposition is separate evidence and never changes these results.
    Finding bodies omit raw matched text, source lines and rule expressions.
    Filename/ref names are fingerprinted in finding source identities as well.
    """
    report = {
        "schemaVersion": 1, "execution": "ERROR", "result": "ERROR",
        "coverage": {"status": "INCOMPLETE", "gaps": []}, "findings": [],
        "termFiles": [], "rules": [], "counts": {}, "errors": [],
        "limits": {
            "maxLineChars": scrub_check.MAX_LINE_CHARS,
            "maxTermBytes": MAX_TERM_BYTES,
            "matches": "First match per rule per line, matching scrub_check behavior",
            "regex": "Python re with trusted explicit terms; a line cap is not a CPU-time bound",
            "scope": "Explicit collected local Git sources only; no remote/platform/unreachable-object clearance",
            "authorizationGranted": False,
        },
    }
    try:
        if type(max_line_chars) is not int or not 1 <= max_line_chars <= MAX_LINE_BUDGET:
            raise _ScanError("invalid-line-budget", "Line budget must be an integer from 1 through 1048576")
        report["limits"]["maxLineChars"] = max_line_chars
        objects, paths, refs, inherited_gaps = _validated(sources)
        rules, report["termFiles"] = _load_rules(term_paths)
        report["rules"] = [{"ruleId": rule["ruleId"], "origins": rule["origins"]} for rule in rules]
        gaps = [dict(row) for row in inherited_gaps]
        findings = []
        text_objects = 0
        source_count = 0
        truncated_lines = 0
        object_bytes = 0

        def scan_text(text: str, identity: dict) -> None:
            nonlocal source_count, truncated_lines
            source_count += 1
            for line_number, line in enumerate(text.splitlines(), 1):
                if len(line) > max_line_chars:
                    truncated_lines += 1
                    gaps.append({"code": "line-truncated", "source": identity,
                                 "line": line_number, "actualChars": len(line),
                                 "scannedChars": max_line_chars})
                    line = line[:max_line_chars]
                for rule in rules:
                    match = rule["pattern"].search(line)
                    if match is not None:
                        evidence = {"source": identity, "ruleId": rule["ruleId"],
                                    "line": line_number, "matchSha256": _digest(match.group(0))}
                        findings.append({"fingerprint": _identity(evidence), **evidence})

        for row in sorted(objects, key=lambda value: value["oid"]):
            data = row["data"]
            object_bytes += len(data)
            identity = {"kind": row["kind"], "oid": row["oid"], "contentSha256": _digest(data)}
            text, issue = _strict_decode(data)
            if issue:
                gaps.append({"code": issue, "source": identity})
            if text is not None:
                first_line = text.splitlines()[0].lstrip("\ufeff") if text.splitlines() else ""
                if row["kind"] == "blob" and first_line == "version https://git-lfs.github.com/spec/v1":
                    # Conservative pointer-shaped text check, not an LFS fetch
                    # or an assertion that its declared external bytes exist.
                    gaps.append({"code": "lfs-payload-unavailable", "source": identity})
                text_objects += 1
                scan_text(text, identity)
        for row in sorted(paths, key=lambda value: (value.get("tree", ""), value["path"], value["oid"], value["mode"])):
            identity = {"kind": "path", "pathSha256": _digest(row["path"]),
                        "oid": row["oid"], "mode": row["mode"]}
            if "tree" in row:
                identity["tree"] = row["tree"]
            try:
                row["path"].encode("utf-8", "strict")
            except UnicodeError:
                gaps.append({"code": "invalid-name-encoding", "source": identity})
            scan_text(row["path"], identity)
            if row["mode"] in {"120000", "160000"}:
                gaps.append({"code": "symlink-target-unfollowed" if row["mode"] == "120000"
                             else "gitlink-payload-unavailable", "source": identity})
        for row in sorted(refs, key=lambda value: value["name"]):
            identity = {"kind": "ref-name", "nameSha256": _digest(row["name"]), "oid": row["oid"]}
            try:
                row["name"].encode("utf-8", "strict")
            except UnicodeError:
                gaps.append({"code": "invalid-name-encoding", "source": identity})
            scan_text(row["name"], identity)
        if text_objects == 0:
            gaps.append({"code": "no-text-object-scanned"})
        report.update(execution="PASS", result="INCOMPLETE" if gaps else "FINDINGS" if findings else "CLEAN_WITHIN_SCOPE")
        report["coverage"] = {"status": "INCOMPLETE" if gaps else "COMPLETE", "gaps": gaps}
        report["findings"] = sorted(findings, key=lambda value: value["fingerprint"])
        report["counts"] = {"objects": len(objects), "paths": len(paths), "refs": len(refs),
                            "textObjectsScanned": text_objects, "sourceFieldsScanned": source_count,
                            "objectBytes": object_bytes, "rules": len(rules), "findings": len(findings),
                            "truncatedLines": truncated_lines, "coverageGaps": len(gaps)}
        # The collector's identity is provenance, not a decision input here.
        for name in ("mode", "selection", "sourceIdentity"):
            if name in sources:
                report[name] = sources[name]
        return report
    except _ScanError as error:
        report["errors"].append({"code": error.code, "message": str(error)})
        return report
    except (OSError, UnicodeError, TypeError, ValueError, RecursionError) as error:
        # Do not echo potentially sensitive regex/source text from exceptions.
        report["errors"].append({"code": "scan-failed", "message": type(error).__name__})
        return report
