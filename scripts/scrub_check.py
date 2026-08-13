"""Publishability gate: fail if tracked text contains project or personal
identifiers.

The transferable tier's contract is zero project nouns, zero personal
data. Generic patterns (secrets, emails) live in scrub_terms.txt
(committed). Project-specific nouns live in scrub_terms.local.txt
(GITIGNORED — the term list itself would otherwise name the project in
the public tree).

Scans `git ls-files` (the publishable set) so gitignored local files are
excluded by construction. Exit 0 = clean; exit 1 with file:line:term hits;
exit 2 = the instrument itself failed (no terms, enumeration failed or
empty, nothing scannable, or a term tier missing under
SCRUB_REQUIRE_LOCAL_TERMS) — never reports clean on a collapsed
denominator.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_TERMS_NAME = "scrub_terms.local.txt"
TERM_FILES = (ROOT / "scripts" / "scrub_terms.txt",
              ROOT / LOCAL_TERMS_NAME)


def load_terms(texts: list[str]) -> list[re.Pattern[str]]:
    patterns = []
    for text in texts:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("re:"):
                patterns.append(re.compile(line[3:], re.IGNORECASE))
            else:
                patterns.append(re.compile(re.escape(line), re.IGNORECASE))
    return patterns


def scan_text(name: str, text: str,
              patterns: list[re.Pattern[str]]) -> list[str]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pat in patterns:
            m = pat.search(line)
            if m:
                hits.append(f"{name}:{lineno}: {m.group(0)!r}")
    return hits


def tracked_files() -> list[Path] | None:
    proc = subprocess.run(["git", "ls-files"], cwd=ROOT,
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        return None
    return [ROOT / p for p in proc.stdout.splitlines() if p.strip()]


def main(argv: list[str]) -> int:
    texts = []
    for f in TERM_FILES:
        if f.is_file():
            texts.append(f.read_text(encoding="utf-8"))
            continue
        if (f.name == LOCAL_TERMS_NAME
                and os.environ.get("SCRUB_REQUIRE_LOCAL_TERMS", "")
                not in ("", "0")):
            print(f"scrub: {f.name} absent with SCRUB_REQUIRE_LOCAL_TERMS "
                  "set — refusing to scan on the generic tier alone")
            return 2
        print(f"scrub: WARNING — term tier {f.name} absent; its patterns "
              "are not being scanned for")
    patterns = load_terms(texts)
    if not patterns:
        print("scrub: no terms loaded — refusing to report clean on an "
              "empty instrument (see prove-an-instrument-can-fail)")
        return 2
    files = tracked_files()
    if files is None:
        print("scrub: git ls-files failed — cannot enumerate the "
              "publishable set (not a git repo?)")
        return 2
    all_hits: list[str] = []
    scanned = 0
    skipped = 0
    for path in files:
        try:
            data = path.read_bytes()
        except OSError:
            skipped += 1
            continue
        if b"\x00" in data[:8192]:
            skipped += 1  # binary — or NUL-bearing text such as UTF-16
            continue
        scanned += 1
        rel = path.relative_to(ROOT).as_posix()
        all_hits.extend(scan_text(rel, data.decode("utf-8", "replace"),
                                  patterns))
    if not scanned:
        print(f"scrub: scanned 0 of {len(files)} tracked files "
              f"({skipped} skipped) — refusing to report clean on an "
              "empty scan")
        return 2
    if all_hits:
        print(f"SCRUB FAILED: {len(all_hits)} hit(s) over {scanned} files:")
        for h in all_hits:
            print(f"  {h}")
        return 1
    print(f"scrub clean: {scanned} tracked text files, "
          f"{len(patterns)} patterns, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
