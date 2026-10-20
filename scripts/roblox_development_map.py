"""Inspect declared development relationships without scheduling or accepting work."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timedelta
import hashlib
import html
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import sys

from roblox_review import exact_keys, safe_absolute

ROOT = Path(__file__).resolve().parents[1]
MAX_MAP = 2 * 1024 * 1024
MAX_EVIDENCE = 256 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
MAX_EDGES = 20000
BASES = {"observed source", "recorded assignment", "prescribed workflow",
         "reviewed evidence", "proposed work", "recorded pending"}
NODE_KINDS = {"scope", "actor", "step", "module", "artifact", "evidence", "correction"}
DIMENSIONS = {"scope", "people", "production", "runtime", "evidence"}
EDGE_KINDS = {"supports", "contains", "depends-on", "assigns", "owns", "calls",
              "data-flow", "produces", "checks", "blocks", "returns-to",
              "supersedes", "learned-from", "coordinates"}
LIMITS = [
    "Relationships, statuses, ownership and evidence bases are supplied declarations, not authenticated facts.",
    "Only depends-on means source depends on target; other edge kinds imply no schedule or execution order.",
    "Tracing follows recorded edges, not proved impact, completeness, authority or acceptance.",
    "Evidence hash checks establish byte identity only; they do not prove the relationship or reported result.",
    "No source extraction, scheduler, Studio operation, build, percentage or promotion is performed.",
    "Bounded non-atomic reads detect common concurrent changes but cannot eliminate filesystem races.",
]


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 8000:
        raise ValueError(f"{label}: expected nonblank text up to 8000 characters")
    return value


def identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,95}", value):
        raise ValueError(f"{label}: invalid identifier")
    return value


def array(value, label, minimum=0, maximum=2000):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label}: expected {minimum}..{maximum} items")
    return value


def enum(value, choices, label):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{label}: expected one of {sorted(choices)}")


def timestamp(value, label):
    text(value, label)
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)", value):
        raise ValueError(f"{label}: expected an explicit UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{label}: timestamp is not UTC")


def digest(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError(f"{label}: expected SHA-256")


def local_path(value, base, *, missing=False):
    raw = text(str(value), "path")
    if "\x00" in raw or raw.startswith(("\\\\", "//")) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", raw):
        raise ValueError("Only local paths are supported; no URLs, shares or device namespaces")
    windows = PureWindowsPath(raw)
    if windows.drive and not windows.is_absolute() or (os.name == "nt" and windows.root and not windows.drive):
        raise ValueError("Drive-relative and rooted-without-drive Windows paths are refused")
    for part in windows.parts:
        if part == windows.anchor or part in {".", ".."}:
            continue
        if (part.endswith((".", " ")) or re.search(r'[<>:"|?*\x00-\x1f]', part)
                or re.match(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", part, re.I)):
            raise ValueError("Unsafe Windows path component or device name")
    path = Path(raw)
    return safe_absolute(path if path.is_absolute() else base / path, missing=missing)


def signature(info):
    # Windows path stat and descriptor fstat can disagree on ctime semantics.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_file(path, limit, *, collect=False):
    path = safe_absolute(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError("Expected a regular file within the byte limit")
    result, chunks, size = hashlib.sha256(), [], 0
    with path.open("rb") as stream:
        if signature(os.fstat(stream.fileno())) != signature(before):
            raise ValueError("File changed before read")
        while chunk := stream.read(min(1024 * 1024, limit - size + 1)):
            size += len(chunk)
            if size > limit:
                raise ValueError("File exceeds byte limit")
            result.update(chunk)
            if collect:
                chunks.append(chunk)
        after = os.fstat(stream.fileno())
    if signature(before) != signature(after) or signature(before) != signature(safe_absolute(path).stat()):
        raise ValueError("File changed during read")
    return result.hexdigest(), size, b"".join(chunks)


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def refs(value, available, label):
    array(value, label, 1)
    for item in value:
        identifier(item, label)
        if item not in available:
            raise ValueError(f"{label}: unknown evidence {item}")
    if len(value) != len(set(value)):
        raise ValueError(f"{label}: duplicate reference")


def edge_key(edge):
    return edge["source"], edge["target"], edge["kind"], edge["relation"]


def validate(value):
    exact_keys(value, {"schemaVersion", "title", "factsCutoffUtc", "builtUtc", "route", "candidate",
                       "basisLegend", "nodes", "views", "crossViewEdges", "evidence", "limits"},
               {"factsCutoffKst", "scopeLegend", "edgeEvidencePolicy"})
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise ValueError("schemaVersion must be integer 1")
    text(value["title"], "title")
    for key in ("factsCutoffKst", "scopeLegend", "edgeEvidencePolicy"):
        if key in value:
            text(value[key], key)
    for key in ("factsCutoffUtc", "builtUtc"):
        timestamp(value[key], key)
    exact_keys(value["route"], {"game", "threadId", "hostId", "task"})
    exact_keys(value["candidate"], {"id", "sha256", "finalVerdict", "reason", "correction"})
    for key, item in value["route"].items():
        text(item, f"route.{key}")
    candidate = value["candidate"]
    for key, item in candidate.items():
        if key not in {"id", "sha256"} or item is not None:
            text(item, f"candidate.{key}")
    if candidate["sha256"] is not None:
        digest(candidate["sha256"], "candidate.sha256")
    if None in (candidate["id"], candidate["sha256"]) and candidate["finalVerdict"] not in {"UNKNOWN", "NOT RUN"}:
        raise ValueError("Missing candidate identity requires UNKNOWN or NOT RUN verdict")
    legend = array(value["basisLegend"], "basisLegend", len(BASES), len(BASES))
    for item in legend:
        enum(item, BASES, "basisLegend")
    if len(set(legend)) != len(BASES):
        raise ValueError("basisLegend must name each basis once")
    for item in array(value["limits"], "limits", 1, 100):
        text(item, "limit")
    evidence = value["evidence"]
    if not isinstance(evidence, dict) or not 1 <= len(evidence) <= 2000:
        raise ValueError("evidence must have 1..2000 entries")
    for key, entry in evidence.items():
        identifier(key, "evidence ID")
        exact_keys(entry, {"path", "sha256", "readUtc", "basis"})
        text(entry["path"], "evidence path")
        digest(entry["sha256"], "evidence digest")
        timestamp(entry["readUtc"], "evidence readUtc")
        text(entry["basis"], "evidence basis description")
    nodes = {}
    for node in array(value["nodes"], "nodes", 1, 1000):
        exact_keys(node, {"id", "label", "status", "owner", "reads", "output", "evidence", "basis", "kind"}, {"level"})
        key = identifier(node["id"], "node ID")
        if key in nodes:
            raise ValueError(f"Duplicate node ID: {key}")
        for field in ("label", "status", "owner", "reads", "output"):
            text(node[field], f"node.{field}")
        enum(node["basis"], BASES, "node basis")
        enum(node["kind"], NODE_KINDS, "node kind")
        refs(node["evidence"], evidence, "node evidence")
        if "level" in node and (type(node["level"]) is not int or not 0 <= node["level"] <= 99):
            raise ValueError("node level must be integer 0..99")
        nodes[key] = node
    count = 0
    def edges(items, members):
        nonlocal count
        seen = set()
        for edge in array(items, "edges", maximum=MAX_EDGES):
            count += 1
            if count > MAX_EDGES:
                raise ValueError("Too many total edge declarations")
            exact_keys(edge, {"source", "target", "relation", "feedback", "kind", "evidence"})
            for key in ("source", "target"):
                identifier(edge[key], key)
                if edge[key] not in members:
                    raise ValueError(f"Edge {key} is absent from its view: {edge[key]}")
            text(edge["relation"], "edge relation")
            enum(edge["kind"], EDGE_KINDS, "edge kind")
            if type(edge["feedback"]) is not bool:
                raise ValueError("feedback must be boolean")
            refs(edge["evidence"], evidence, "edge evidence")
            key = edge_key(edge)
            if key in seen:
                raise ValueError(f"Duplicate edge: {key}")
            seen.add(key)
    views, all_members = set(), set()
    for view in array(value["views"], "views", 1, 20):
        exact_keys(view, {"id", "label", "context", "dimension", "rows", "edges"})
        key = identifier(view["id"], "view ID")
        if key in views:
            raise ValueError(f"Duplicate view ID: {key}")
        views.add(key)
        text(view["label"], "view label"); text(view["context"], "view context")
        enum(view["dimension"], DIMENSIONS, "view dimension")
        members = set()
        for row in array(view["rows"], "rows", 1, 1000):
            for key in array(row, "row", 1, 1000):
                if key is None:
                    continue
                identifier(key, "row node")
                if key not in nodes or key in members:
                    raise ValueError(f"Unknown or repeated view member: {key}")
                members.add(key)
        if not members:
            raise ValueError("View has no nodes")
        all_members.update(members)
        edges(view["edges"], members)
    if all_members != set(nodes):
        raise ValueError("Every node must belong to at least one view")
    edges(value["crossViewEdges"], nodes)
    # A repeated relationship across views may carry extra references, not conflicting flags.
    all_edges(value)
    return value


def load_map(path):
    path = local_path(path, Path.cwd())
    sha, _, raw = read_file(path, MAX_MAP, collect=True)
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                       parse_constant=lambda item: (_ for _ in ()).throw(ValueError(f"Nonfinite JSON: {item}")))
    return validate(value), path, sha


def all_edges(value):
    result = {}
    for edge in [edge for view in value["views"] for edge in view["edges"]] + value["crossViewEdges"]:
        key = edge_key(edge)
        if key not in result:
            result[key] = dict(edge, evidence=list(edge["evidence"]))
        else:
            if result[key]["feedback"] != edge["feedback"]:
                raise ValueError("Repeated edge has conflicting feedback flags")
            result[key]["evidence"] = sorted(set(result[key]["evidence"] + edge["evidence"]))
    return [result[key] for key in sorted(result)]


def verify_evidence(value, map_path):
    results, remaining = [], MAX_TOTAL
    for key, entry in sorted(value["evidence"].items()):
        row = {"id": key, "path": entry["path"], "expectedSha256": entry["sha256"]}
        try:
            path = local_path(entry["path"], map_path.parent)
            size = path.stat().st_size
            if size > remaining:
                raise ValueError("Aggregate evidence byte limit exceeded")
            remaining -= size
            actual, size, _ = read_file(path, min(MAX_EVIDENCE, size))
            row.update(actualSha256=actual, bytes=size,
                       status="matched" if actual == entry["sha256"].lower() else "drift")
        except (OSError, ValueError) as error:
            row.update(status="unavailable", error=str(error))
        results.append(row)
    return results


def trace(value, node, direction="both", depth=1, kinds=()):
    if node not in {item["id"] for item in value["nodes"]}:
        raise ValueError(f"Unknown start node: {node}")
    enum(direction, {"in", "out", "both"}, "trace direction")
    if type(depth) is not int or not 1 <= depth <= 8:
        raise ValueError("trace depth must be integer 1..8")
    for kind in kinds:
        enum(kind, EDGE_KINDS, "trace kind")
    edges = [edge for edge in all_edges(value) if not kinds or edge["kind"] in kinds]
    adjacency = {}
    for index, edge in enumerate(edges):
        if direction in {"out", "both"}:
            adjacency.setdefault(edge["source"], []).append((edge["target"], index))
        if direction in {"in", "both"}:
            adjacency.setdefault(edge["target"], []).append((edge["source"], index))
    distance, selected, queue = {node: 0}, set(), deque([node])
    while queue:
        current = queue.popleft()
        if distance[current] >= depth:
            continue
        for neighbor, index in adjacency.get(current, []):
            selected.add(index)
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    nodes = [item for item in value["nodes"] if item["id"] in distance]
    chosen = [edges[index] for index in sorted(selected)]
    refs_used = {ref for item in nodes + chosen for ref in item["evidence"]}
    return {"start": node, "direction": direction, "depth": depth, "kinds": sorted(set(kinds)),
            "distances": distance, "nodes": nodes, "edges": chosen,
            "evidence": {key: value["evidence"][key] for key in sorted(refs_used)}, "limits": LIMITS + value["limits"]}


def differences(before, after):
    return {key: {"before": before.get(key), "after": after.get(key)}
            for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}


def compare(before, after):
    def collection(left, right):
        return {"added": [right[k] for k in sorted(right.keys() - left.keys())],
                "removed": [left[k] for k in sorted(left.keys() - right.keys())],
                "changed": [{"id": k, "fields": differences(left[k], right[k])}
                            for k in sorted(left.keys() & right.keys()) if left[k] != right[k]]}
    edge_id = lambda e: json.dumps(edge_key(e), ensure_ascii=True, separators=(",", ":"))
    metadata = lambda v: {k: item for k, item in v.items() if k not in {"nodes", "views", "crossViewEdges", "evidence", "candidate"}}
    candidate_id = lambda v: (v["candidate"]["id"], (v["candidate"]["sha256"] or "").lower())
    return {"candidate": differences(before["candidate"], after["candidate"]),
            "candidateIdentityChanged": candidate_id(before) != candidate_id(after),
            "metadata": differences(metadata(before), metadata(after)),
            "nodes": collection({n["id"]: n for n in before["nodes"]}, {n["id"]: n for n in after["nodes"]}),
            "edges": collection({edge_id(e): e for e in all_edges(before)}, {edge_id(e): e for e in all_edges(after)}),
            "evidence": collection(before["evidence"], after["evidence"]),
            "views": collection({v["id"]: v for v in before["views"]}, {v["id"]: v for v in after["views"]}),
            "limits": LIMITS + ["Candidate verdicts remain declarations attached to their own map; no acceptance is transferred."]}


def markdown(value):
    if value is None:
        return "unknown"
    escaped = html.escape(str(value), quote=True).replace("\r", "").replace("\n", "<br>")
    return re.sub(r"([\\`*_{}\[\]()#!|~])", r"\\\1", escaped)


def mermaid(value):
    return "".join(c if c.isalnum() or c in " .,:/-" else f"#{ord(c)};" for c in str(value).replace("\n", " ").replace("\r", " "))


def render_report(value, sha):
    lines = [f"# {markdown(value['title'])}", "", f"Map SHA-256: `{sha}`", "",
             f"Facts cutoff: {markdown(value['factsCutoffUtc'])}; built: {markdown(value['builtUtc'])}", "",
             "Statuses and edges below are declarations. This report does not verify evidence files.", "", "## Route and candidate", ""]
    for group in ("route", "candidate"):
        for key, item in value[group].items():
            lines.append(f"- {markdown(group + '.' + key)}: {markdown(item)}")
    nodes = {node["id"]: node for node in value["nodes"]}
    aliases = {key: f"n{index}" for index, key in enumerate(sorted(nodes))}
    def view_section(label, context, members, edges):
        lines.extend(["", f"## {markdown(label)}", "", markdown(context), "", "```mermaid", "flowchart LR"])
        for key in members:
            lines.append(f'  {aliases[key]}["{mermaid(nodes[key]["label"])}"]')
        for edge in edges:
            label = mermaid(edge["kind"] + ": " + edge["relation"])
            lines.append(f'  {aliases[edge["source"]]} -->|"{label}"| {aliases[edge["target"]]}')
        lines.extend(["```", "", "| Source | Kind / relation | Target | Feedback | Evidence |", "|---|---|---|---|---|"])
        for edge in edges:
            cells = [edge["source"], edge["kind"] + ": " + edge["relation"], edge["target"], str(edge["feedback"]), ", ".join(edge["evidence"])]
            lines.append("| " + " | ".join(map(markdown, cells)) + " |")
    for view in value["views"]:
        members = [key for row in view["rows"] for key in row if key is not None]
        view_section(view["label"], view["dimension"] + ": " + view["context"], members, view["edges"])
    if value["crossViewEdges"]:
        edges = value["crossViewEdges"]
        view_section("Cross-view relationships", "Recorded connections across views.", sorted({e[k] for e in edges for k in ("source", "target")}), edges)
    lines.extend(["", "## Node declarations", "", "| ID / kind | Label / status | Owner | Reads | Output | Basis / evidence |", "|---|---|---|---|---|---|"])
    for node in value["nodes"]:
        cells = [node["id"] + " / " + node["kind"], node["label"] + " / " + node["status"], node["owner"], node["reads"], node["output"], node["basis"] + " / " + ", ".join(node["evidence"])]
        lines.append("| " + " | ".join(map(markdown, cells)) + " |")
    lines.extend(["", "## Evidence references", ""])
    for key, entry in sorted(value["evidence"].items()):
        lines.append(f"- {markdown(key)}: {markdown(entry['path'])}; SHA-256 `{entry['sha256']}`; read {markdown(entry['readUtc'])}; {markdown(entry['basis'])}")
    lines.extend(["", "## Limits", ""] + ["- " + markdown(item) for item in LIMITS + value["limits"]])
    return "\n".join(lines) + "\n"


def write_report(value, sha, output):
    raw = text(str(output), "output")
    if ".." in raw.replace("\\", "/").split("/"):
        raise ValueError("Output traversal is refused")
    path = local_path(raw, Path.cwd(), missing=True)
    root = safe_absolute(ROOT / "team" / "development-maps", missing=True)
    if not path.is_relative_to(root) or path == root or path.suffix.lower() != ".md":
        raise ValueError("Report must be a new .md file beneath team/development-maps")
    if path.exists():
        raise ValueError("Report output already exists")
    content = render_report(value, sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_absolute(path, missing=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
    return {"path": str(path), "sha256": hashlib.sha256(content.encode()).hexdigest(), "limits": LIMITS}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True)
        for command in ("check", "trace", "report"):
            sub = commands.add_parser(command); sub.add_argument("--map", required=True)
            if command == "check":
                sub.add_argument("--verify-evidence", action="store_true")
            elif command == "report":
                sub.add_argument("--out", required=True)
            else:
                sub.add_argument("--node", required=True)
                sub.add_argument("--direction", choices=["in", "out", "both"], default="both")
                sub.add_argument("--depth", type=int, default=1)
                sub.add_argument("--kind", choices=sorted(EDGE_KINDS), action="append", default=[])
        sub = commands.add_parser("compare"); sub.add_argument("--before", required=True); sub.add_argument("--after", required=True)
        args = parser.parse_args(argv)
        code = 0
        if args.command == "compare":
            before, _, before_sha = load_map(args.before); after, _, after_sha = load_map(args.after)
            result = dict(compare(before, after), beforeMapSha256=before_sha, afterMapSha256=after_sha)
        else:
            value, path, sha = load_map(args.map)
            if args.command == "check":
                result = {"status": "structure-valid", "mapSha256": sha, "nodes": len(value["nodes"]), "edges": len(all_edges(value)), "evidenceStatus": "not-checked", "limits": LIMITS + value["limits"]}
                if args.verify_evidence:
                    rows = verify_evidence(value, path)
                    code = 2 if any(row["status"] != "matched" for row in rows) else 0
                    result.update(evidenceStatus="mismatch-or-unavailable" if code else "matched", evidence=rows)
            elif args.command == "trace":
                result = dict(trace(value, args.node, args.direction, args.depth, args.kind), mapSha256=sha)
            else:
                result = write_report(value, sha, args.out)
        print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
        return code
    except (OSError, ValueError, TypeError, RecursionError) as error:
        print(json.dumps({"status": "error", "error": str(error), "limits": LIMITS}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
