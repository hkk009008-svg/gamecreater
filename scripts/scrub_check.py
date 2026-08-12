"""Publishability gate: fail if tracked text contains project or personal
identifiers.

The transferable tier's contract is zero project nouns, zero personal
data. Generic patterns (secrets, emails) live in scrub_terms.txt
(committed). Project-specific nouns live in scrub_terms.local.txt
(GITIGNORED — the term list itself would otherwise name the project in
the public tree).

Scans `git ls-files` (the publishable set) so gitignored local files are
excluded by construction. Exit 0 = clean; exit 1 with file:line:term hits.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERM_FILES = (ROOT / "scripts" / "scrub_terms.txt",
              ROOT / "scrub_terms.local.txt")


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


def tracked_files() -> list[Path]:
    proc = subprocess.run(["git", "ls-files"], cwd=ROOT,
                          capture_output=True, text=True, timeout=60)
    return [ROOT / p for p in proc.stdout.splitlines() if p.strip()]


def main(argv: list[str]) -> int:
    texts = [f.read_text(encoding="utf-8") for f in TERM_FILES if f.is_file()]
    patterns = load_terms(texts)
    if not patterns:
        print("scrub: no terms loaded — refusing to report clean on an "
              "empty instrument (see prove-an-instrument-can-fail)")
        return 1
    all_hits: list[str] = []
    scanned = 0
    for path in tracked_files():
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:8192]:
            continue  # binary
        scanned += 1
        rel = path.relative_to(ROOT).as_posix()
        all_hits.extend(scan_text(rel, data.decode("utf-8", "replace"),
                                  patterns))
    if all_hits:
        print(f"SCRUB FAILED: {len(all_hits)} hit(s) over {scanned} files:")
        for h in all_hits:
            print(f"  {h}")
        return 1
    print(f"scrub clean: {scanned} tracked text files, "
          f"{len(patterns)} patterns")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
