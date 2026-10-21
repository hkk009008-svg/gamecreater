"""Offline Git publication audit; a report supplies neither clearance nor authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
MAX_OBJECT_BUDGET = 128 * 1024 * 1024
MAX_TOTAL_BUDGET = 160 * 1024 * 1024


class AuditInputError(ValueError):
    pass


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditInputError("Duplicate JSON key")
        result[key] = value
    return result


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode()).hexdigest()


def output_path(value: str) -> Path:
    from roblox_review import safe_absolute
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = safe_absolute(path, missing=True)
    team = safe_absolute(ROOT / "team")
    if (not path.is_relative_to(team) or not path.name.endswith(".local.json")
            or not path.parent.is_dir() or path.exists()):
        raise AuditInputError("Use a new .local.json report below the harness team directory")
    return path


def dispositions(path: Path | None, identity: str, findings: list[dict]) -> dict:
    result = {"requested": path is not None, "entries": [],
              "unclassifiedCount": len(findings)}
    if path is None:
        return result
    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise AuditInputError("Disposition file exceeds its declared limit")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys)
    if (not isinstance(data, dict)
            or set(data) != {"schemaVersion", "scanIdentity", "entries"}
            or type(data["schemaVersion"]) is not int or data["schemaVersion"] != 1
            or data["scanIdentity"] != identity or not isinstance(data["entries"], list)):
        raise AuditInputError("Disposition identity/schema mismatch")
    known = {entry["fingerprint"] for entry in findings}
    if len(known) != len(findings):
        raise AuditInputError("Finding fingerprints are not unique")
    seen = set()
    classes = {"synthetic-fixture", "baseline-existing", "action-required", "reviewed-reference"}
    for entry in data["entries"]:
        if (not isinstance(entry, dict)
                or set(entry) != {"fingerprint", "classification", "rationale"}
                or not isinstance(entry["fingerprint"], str)
                or entry["fingerprint"] not in known or entry["fingerprint"] in seen
                or not isinstance(entry["classification"], str)
                or entry["classification"] not in classes
                or not isinstance(entry["rationale"], str)
                or not entry["rationale"].strip() or len(entry["rationale"]) > 1000):
            raise AuditInputError("Invalid, duplicate or stale finding disposition")
        seen.add(entry["fingerprint"])
        result["entries"].append(entry)
    result.update(fileSha256=hashlib.sha256(raw).hexdigest(),
                  unclassifiedCount=len(known - seen),
                  limit="Reviewer declarations only; raw findings and result remain unchanged")
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    selection = p.add_mutually_exclusive_group(required=True)
    selection.add_argument("--tree", metavar="REV")
    selection.add_argument("--index", action="store_true")
    selection.add_argument("--refs", action="store_true")
    p.add_argument("--local-terms", action="append", default=[], metavar="FILE")
    p.add_argument("--dispositions", type=Path)
    p.add_argument("--max-object-bytes", type=int, default=None,
                   help="Explicit object budget, at most 128 MiB; default remains 4 MiB")
    p.add_argument("--max-total-bytes", type=int, default=None,
                   help="Explicit total payload budget, at most 160 MiB; default remains 64 MiB")
    p.add_argument("--max-line-chars", type=int, default=None,
                   help="Explicit scan line budget, at most 1048576; default remains 4096")
    p.add_argument("--out", required=True, metavar="NEW.local.json")
    return p


def budgets(args) -> tuple[dict, dict]:
    """Bound explicit investigations without changing ordinary audit defaults."""
    from publication_git import DEFAULT_LIMITS
    from publication_scan import MAX_LINE_BUDGET
    collection, scan = {}, {}
    for attribute, ceiling in (("max_object_bytes", MAX_OBJECT_BUDGET),
                               ("max_total_bytes", MAX_TOTAL_BUDGET),
                               ("max_line_chars", MAX_LINE_BUDGET)):
        value = getattr(args, attribute)
        if value is None:
            continue
        if type(value) is not int or not 1 <= value <= ceiling:
            raise AuditInputError("Explicit audit budget is outside its supported range")
        (scan if attribute == "max_line_chars" else collection)[attribute] = value
    effective = {**DEFAULT_LIMITS, **collection}
    if effective["max_object_bytes"] > effective["max_total_bytes"]:
        raise AuditInputError("Object budget cannot exceed total payload budget")
    return collection, scan


def validate_scan(scan) -> None:
    if not isinstance(scan, dict) or scan.get("result") not in {
            "CLEAN_WITHIN_SCOPE", "FINDINGS", "INCOMPLETE", "ERROR"}:
        raise AuditInputError("Scanner returned an invalid result")
    if scan["result"] == "ERROR":
        if scan.get("execution") != "ERROR":
            raise AuditInputError("Scanner error status is inconsistent")
        return
    findings, coverage = scan.get("findings"), scan.get("coverage")
    if (scan.get("execution") != "PASS" or not isinstance(findings, list)
            or not isinstance(coverage, dict)
            or coverage.get("status") not in {"COMPLETE", "INCOMPLETE"}
            or not isinstance(coverage.get("gaps"), list)
            or (coverage["status"] == "COMPLETE") != (len(coverage["gaps"]) == 0)):
        raise AuditInputError("Scanner coverage/status is missing")
    expected = ("INCOMPLETE" if coverage["status"] == "INCOMPLETE" else
                "FINDINGS" if findings else "CLEAN_WITHIN_SCOPE")
    if scan["result"] != expected:
        raise AuditInputError("Scanner findings/coverage/result disagree")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        destination = output_path(args.out)
    except BaseException as error:
        print(json.dumps({"execution": "ERROR", "stage": "output",
                          "errorType": type(error).__name__}), file=sys.stderr)
        return 2
    stage = "collection"
    report = {"schemaVersion": 1, "execution": "ERROR", "result": "ERROR",
              "authorityGranted": False, "publicationClearance": False,
              "request": {"repo": args.repo, "tree": args.tree,
                          "mode": "tree" if args.tree is not None else "index" if args.index else "refs",
                          "localTerms": args.local_terms}}
    requested = {name: getattr(args, name) for name in (
        "max_object_bytes", "max_total_bytes", "max_line_chars")
        if getattr(args, name) is not None}
    if requested:
        report["request"]["budgets"] = requested
    try:
        from publication_git import collect_sources
        from publication_scan import scan_sources
        if not args.repo.strip() or (args.tree is not None and not args.tree.strip()):
            raise AuditInputError("Repository and target must be nonblank")
        stage = "limits"
        collection_budget, scan_budget = budgets(args)
        if requested:
            from publication_git import DEFAULT_LIMITS
            from scrub_check import MAX_LINE_CHARS
            report["budgets"] = {
                "collector": {**DEFAULT_LIMITS, **collection_budget},
                "scanner": {"maxLineChars": scan_budget.get("max_line_chars", MAX_LINE_CHARS)},
            }
        mode = "tree" if args.tree is not None else "index" if args.index else "refs"
        stage = "collection"
        sources = collect_sources(Path(args.repo), mode, target=args.tree,
                                  **({"limits": collection_budget} if collection_budget else {}))
        terms = [ROOT / "scripts" / "scrub_terms.txt", *map(Path, args.local_terms)]
        stage = "scan"
        scan = scan_sources(sources, terms, **scan_budget)
        validate_scan(scan)
        report.update(scan)
        report.update(rawScanResult=scan["result"], authorityGranted=False, publicationClearance=False,
                      source={key: sources.get(key) for key in (
                          "repository", "mode", "selection", "sourceIdentity", "counts")},
                      termScope="generic-plus-explicit-local" if args.local_terms else "generic-only")
        report["scanIdentity"] = digest(report)
        stage = "dispositions"
        report["dispositions"] = dispositions(args.dispositions, report["scanIdentity"],
                                                report.get("findings", []))
        report["limits"] = {"scanner": report.get("limits"),
                            "scope": "Selected local Git content only; no remote hosting surface, "
                                     "reflog/unreachable object, external payload, host activation "
                                     "or authorization claim"}
    except BaseException as error:
        # Never copy untrusted Git stderr or exception text into this error.
        report.update(execution="ERROR", result="ERROR",
                      error={"stage": stage, "type": type(error).__name__})
        code = getattr(error, "code", None)
        if isinstance(code, str) and re.fullmatch(r"[a-z_]{1,80}", code):
            report["error"]["code"] = code
    try:
        data = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    except BaseException as error:
        print(json.dumps({"execution": "ERROR", "stage": "write",
                          "errorType": type(error).__name__}), file=sys.stderr)
        return 2
    result = report["result"]
    print(json.dumps({"execution": report["execution"], "result": result,
                      "findingCount": len(report.get("findings", [])),
                      "report": str(destination)}, ensure_ascii=True))
    return 0 if result == "CLEAN_WITHIN_SCOPE" else 1 if result == "FINDINGS" else 2


if __name__ == "__main__":
    sys.exit(main())
