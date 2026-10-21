"""Collect pinned local Git bytes for an offline publication-content audit.

No checkout, filters, network, index write or object write is performed. Limits
bound accepted enumeration/payload sizes and each Git wait, not OS memory use
or arbitrary filesystem stalls. Ref mode covers current local refs plus HEAD;
reflogs, unreachable objects, other clones and hosting surfaces are not selected.
Inspection-only ``-c`` overrides are per Git invocation; repository configuration
and the host's session hooks/trust are never rewritten.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


DEFAULT_LIMITS = {
    "max_objects": 20000,
    "max_object_bytes": 4 * 1024 * 1024,
    "max_total_bytes": 64 * 1024 * 1024,
    "max_tree_entries": 50000,
    "timeout": 20,
}


class AuditError(ValueError):
    """A sanitized collector failure; never contains Git output or payloads."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _limits(overrides):
    result = dict(DEFAULT_LIMITS)
    if overrides is not None:
        if not isinstance(overrides, dict) or set(overrides) - set(result):
            raise AuditError("invalid_limits")
        result.update(overrides)
    if any(type(value) is not int or value <= 0 for value in result.values()):
        raise AuditError("invalid_limits")
    return result


class _Git:
    def __init__(self, repo, limits):
        try:
            self.repo = Path(repo).resolve(strict=True)
        except (OSError, ValueError, TypeError):
            raise AuditError("invalid_repository") from None
        if not self.repo.is_dir():
            raise AuditError("invalid_repository")
        self.limits = limits
        self.env = {key: value for key, value in os.environ.items()
                    if not key.upper().startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0",
                        GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1",
                        GIT_GRAFT_FILE=os.devnull)
        bare = self.run(["rev-parse", "--is-bare-repository"]).strip()
        if bare == b"false":
            root = self.run(["rev-parse", "--show-toplevel"]).strip()
        elif bare == b"true":
            root = self.run(["rev-parse", "--absolute-git-dir"]).strip()
        else:
            raise AuditError("invalid_repository_kind")
        try:
            self.repo = Path(os.fsdecode(root)).resolve(strict=True)
        except (ValueError, OSError):
            raise AuditError("invalid_repository_root") from None
        form = self.run(["rev-parse", "--show-object-format"]).strip()
        if form not in {b"sha1", b"sha256"}:
            raise AuditError("unsupported_object_format")
        self.algorithm = form.decode("ascii")
        self.oid_size = 40 if form == b"sha1" else 64

    def run(self, args, *, data=None, optional=False):
        command = ["git", "--no-pager", "--no-replace-objects",
                   "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
                   "-c", f"core.hooksPath={os.devnull}", "-c", "protocol.allow=never",
                   "-C", str(self.repo), *args]
        try:
            result = subprocess.run(command, input=data, capture_output=True,
                                    timeout=self.limits["timeout"], env=self.env)
        except (OSError, subprocess.TimeoutExpired):
            raise AuditError("git_execution_failed") from None
        if result.returncode != 0:
            if optional and result.returncode == 1:
                return None
            raise AuditError("git_command_failed")
        # Accepted output is bounded after the subprocess returns. This is not
        # an OS allocation bound; callers must retain that limitation.
        cap = (self.limits["max_total_bytes"]
               + self.limits["max_objects"] * 256
               + self.limits["max_tree_entries"] * 512)
        if len(result.stdout) > cap:
            raise AuditError("git_output_limit")
        return result.stdout

    def oid(self, raw):
        if not re.fullmatch(rb"[0-9a-f]{" + str(self.oid_size).encode() + rb"}", raw):
            raise AuditError("invalid_object_identity")
        return raw.decode("ascii")

    def tree(self, target):
        if (not isinstance(target, str) or not target.strip()
                or target.startswith("-") or "\x00" in target
                or "\n" in target or "\r" in target):
            raise AuditError("invalid_tree_target")
        raw = self.run(["rev-parse", "--verify", "--end-of-options", target + "^{tree}"])
        return self.oid(raw.strip())


def _records(raw):
    if not raw or not raw.endswith(b"\x00"):
        raise AuditError("empty_or_malformed_entries")
    return raw[:-1].split(b"\x00")


def _path(raw):
    if not raw or b"\x00" in raw:
        raise AuditError("invalid_path_entry")
    return raw.decode("utf-8", "surrogateescape")


def _index_paths(git, raw):
    paths = []
    for record in _records(raw):
        try:
            header, name = record.split(b"\t", 1)
            mode, oid, stage = header.split(b" ")
        except ValueError:
            raise AuditError("malformed_index_entry") from None
        if stage != b"0":
            raise AuditError("unmerged_index")
        if mode not in {b"100644", b"100755", b"120000", b"160000"}:
            raise AuditError("unsupported_index_mode")
        paths.append({"path": _path(name), "oid": git.oid(oid),
                      "mode": mode.decode("ascii")})
    return paths


def _tree_paths(git, raw):
    paths = []
    for record in _records(raw):
        try:
            header, name = record.split(b"\t", 1)
            mode, kind, oid = header.split(b" ")
        except ValueError:
            raise AuditError("malformed_tree_entry") from None
        if (mode not in {b"100644", b"100755", b"120000", b"160000"}
                or kind != (b"commit" if mode == b"160000" else b"blob")):
            raise AuditError("unsupported_tree_mode")
        paths.append({"path": _path(name), "oid": git.oid(oid),
                      "mode": mode.decode("ascii")})
    return paths


def _refs(git):
    raw = git.run(["for-each-ref", "--format=%(refname)%00%(objectname)"])
    refs = []
    for line in raw.splitlines():
        try:
            name, oid = line.split(b"\x00")
        except ValueError:
            raise AuditError("malformed_ref_entry") from None
        if not name.startswith(b"refs/") or not name:
            raise AuditError("malformed_ref_entry")
        refs.append({"name": name.decode("utf-8", "surrogateescape"), "oid": git.oid(oid)})
    head = git.run(["rev-parse", "--verify", "--quiet", "HEAD"], optional=True)
    if head:
        refs.append({"name": "HEAD", "oid": git.oid(head.strip())})
    if not refs:
        raise AuditError("empty_ref_selection")
    if len(refs) > git.limits["max_objects"]:
        raise AuditError("ref_limit")
    return refs


def _object_payloads(git, oids):
    if not oids or len(oids) > git.limits["max_objects"]:
        raise AuditError("empty_or_excessive_objects")
    oids = sorted(set(oids))
    request = "".join(oid + "\n" for oid in oids).encode("ascii")
    raw = git.run(["cat-file", "--batch-check"], data=request)
    lines = raw.splitlines()
    if len(lines) != len(oids):
        raise AuditError("object_inventory_mismatch")
    metadata = []
    total = 0
    for expected, line in zip(oids, lines):
        fields = line.split(b" ")
        if (len(fields) != 3 or git.oid(fields[0]) != expected
                or fields[1] not in {b"blob", b"tree", b"commit", b"tag"}
                or not fields[2].isdigit()):
            raise AuditError("invalid_object_inventory")
        size = int(fields[2])
        if size > git.limits["max_object_bytes"]:
            raise AuditError("object_size_limit")
        total += size
        if total > git.limits["max_total_bytes"]:
            raise AuditError("total_size_limit")
        metadata.append((expected, fields[1].decode("ascii"), size))
    raw = git.run(["cat-file", "--batch"], data=request)
    cursor = 0
    objects = []
    for oid, kind, size in metadata:
        header = f"{oid} {kind} {size}\n".encode("ascii")
        if not raw.startswith(header, cursor):
            raise AuditError("object_payload_header_mismatch")
        cursor += len(header)
        payload = raw[cursor:cursor + size]
        cursor += size
        if len(payload) != size or raw[cursor:cursor + 1] != b"\n":
            raise AuditError("object_payload_truncated")
        cursor += 1
        digest = hashlib.new(git.algorithm, f"{kind} {size}\0".encode("ascii") + payload).hexdigest()
        if digest != oid:
            raise AuditError("object_payload_identity_mismatch")
        objects.append({"oid": oid, "kind": kind, "data": payload})
    if cursor != len(raw):
        raise AuditError("object_payload_trailing_data")
    return objects, total


def _historic_paths(git, objects, refs):
    nodes = {}
    oid_bytes = git.oid_size // 2
    for obj in objects:
        if obj["kind"] != "tree":
            continue
        entries = []
        data = obj["data"]
        cursor = 0
        while cursor < len(data):
            try:
                space = data.index(b" ", cursor)
                nul = data.index(b"\0", space + 1)
            except ValueError:
                raise AuditError("malformed_historic_tree") from None
            mode = data[cursor:space].zfill(6)
            name = data[space + 1:nul]
            raw_oid = data[nul + 1:nul + 1 + oid_bytes]
            if (len(raw_oid) != oid_bytes or not name or b"/" in name
                    or mode not in {b"040000", b"100644", b"100755", b"120000", b"160000"}):
                raise AuditError("malformed_historic_tree")
            entries.append({"path": _path(name), "oid": raw_oid.hex(),
                            "mode": mode.decode("ascii")})
            if len(entries) > git.limits["max_tree_entries"]:
                raise AuditError("tree_entry_limit")
            cursor = nul + 1 + oid_bytes
        nodes[obj["oid"]] = entries
    inventory = {obj["oid"]: obj for obj in objects}
    roots = set()
    for obj in objects:
        if obj["kind"] == "commit":
            first = obj["data"].split(b"\n", 1)[0]
            if not first.startswith(b"tree "):
                raise AuditError("malformed_commit_tree")
            roots.add(git.oid(first[5:]))
    # A tree ref/tag selects that tree as a root even if it is otherwise only
    # a nested directory in a commit. No ref target is executed or fetched.
    for ref in refs:
        current = ref["oid"]
        seen = set()
        while current in inventory and inventory[current]["kind"] == "tag":
            if current in seen:
                raise AuditError("cyclic_tag_selection")
            seen.add(current)
            first = inventory[current]["data"].split(b"\n", 1)[0]
            if not first.startswith(b"object "):
                raise AuditError("malformed_tag_target")
            current = git.oid(first[7:])
        if current in nodes:
            roots.add(current)
    paths = []
    # Expand every distinct root, rather than scan detached path components:
    # a configured nested/path marker must retain that complete spelling.
    for root in sorted(roots):
        stack = [(root, "", frozenset())]
        while stack:
            tree, prefix, ancestors = stack.pop()
            if tree in ancestors or tree not in nodes:
                raise AuditError("missing_or_cyclic_historic_tree")
            for entry in nodes[tree]:
                full = prefix + entry["path"]
                paths.append({**entry, "path": full, "tree": root})
                if len(paths) > git.limits["max_tree_entries"]:
                    raise AuditError("tree_entry_limit")
                if entry["mode"] == "040000":
                    stack.append((entry["oid"], full + "/", ancestors | {tree}))
    return paths


def _shallow_status(git):
    value = git.run(["rev-parse", "--is-shallow-repository"]).strip()
    if value not in {b"true", b"false"}:
        raise AuditError("invalid_shallow_status")
    return value == b"true"


def _parent_gaps(git, objects):
    """Cross-check canonical raw parents independently of Git traversal overlays."""
    inventory = {obj["oid"]: obj for obj in objects}
    gaps = []
    for obj in objects:
        if obj["kind"] != "commit":
            continue
        header, separator, _ = obj["data"].partition(b"\n\n")
        if not separator:
            raise AuditError("malformed_commit_headers")
        for line in header.split(b"\n"):
            if not line.startswith(b"parent "):
                continue
            parent = git.oid(line[7:])
            if parent not in inventory:
                gaps.append({"kind": "history_parent_unavailable", "commit": obj["oid"],
                             "parent": parent})
            elif inventory[parent]["kind"] != "commit":
                raise AuditError("invalid_commit_parent_kind")
    return gaps


def collect_sources(repo, mode, target=None, limits=None):
    """Return immutable payloads and explicit local selection identity.

    ``refs`` paths are full paths keyed by root ``tree`` OID, rather than
    pretending one historical filename has only one payload.
    Tree/index modes select full paths; they do not select commit identities.
    """
    bounds = _limits(limits)
    if (not isinstance(mode, str) or mode not in {"tree", "index", "refs"}
            or (mode != "tree" and target is not None)):
        raise AuditError("invalid_selection")
    git = _Git(repo, bounds)
    refs = []
    if mode == "tree":
        selected = git.tree(target)
        paths = _tree_paths(git, git.run(["ls-tree", "-r", "-z", "--full-tree", selected]))
        oids = [item["oid"] for item in paths if item["mode"] != "160000"]
        selection = {"target": target, "tree": selected}
        unchanged = lambda: git.tree(target) == selected
    elif mode == "index":
        selected = git.run(["ls-files", "--stage", "-z", "--full-name"])
        paths = _index_paths(git, selected)
        oids = [item["oid"] for item in paths if item["mode"] != "160000"]
        selection = {"indexEntriesSha256": hashlib.sha256(selected).hexdigest()}
        unchanged = lambda: git.run(["ls-files", "--stage", "-z", "--full-name"]) == selected
    else:
        shallow_before = _shallow_status(git)
        refs = _refs(git)
        selection = {"refs": refs, "shallow": shallow_before}
        targets = "".join(oid + "\n" for oid in sorted({ref["oid"] for ref in refs}))
        raw = git.run(["rev-list", "--objects", "--no-object-names", "--stdin"],
                      data=targets.encode("ascii"))
        oids = [git.oid(line) for line in raw.splitlines()]
        paths = []
        unchanged = lambda: _refs(git) == refs
    if len(paths) > bounds["max_tree_entries"]:
        raise AuditError("tree_entry_limit")
    objects, total = _object_payloads(git, oids)
    if mode == "refs":
        paths = _historic_paths(git, objects, refs)
    if not unchanged():
        raise AuditError("selection_changed_during_collection")
    gaps = [{"kind": "external_symlink_target" if item["mode"] == "120000" else "external_gitlink",
             "path": item["path"], "oid": item["oid"], **({"tree": item["tree"]} if "tree" in item else {})}
            for item in paths if item["mode"] in {"120000", "160000"}]
    if mode == "refs":
        if _shallow_status(git) != shallow_before:
            raise AuditError("history_boundary_changed_during_collection")
        gaps.extend(_parent_gaps(git, objects))
        if shallow_before:
            gaps.append({"kind": "shallow_history"})
    kinds = {kind: sum(obj["kind"] == kind for obj in objects)
             for kind in ("blob", "tree", "commit", "tag")}
    kept = [obj for obj in objects if obj["kind"] != "tree"]
    if not kept:
        raise AuditError("no_scannable_object_selection")
    identity = hashlib.sha256(json.dumps(
        {"mode": mode, "selection": selection, "algorithm": git.algorithm},
        sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
    return {"repository": str(git.repo), "mode": mode, "selection": selection,
            "objects": kept, "paths": paths, "refs": refs, "coverageGaps": gaps,
            "counts": {"objectCount": len(kept), "gitObjectCount": len(objects),
                       "byteCount": total, "pathCount": len(paths), "refCount": len(refs),
                       **{kind + "Count": count for kind, count in kinds.items()}},
            "sourceIdentity": identity}
