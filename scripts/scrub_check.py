"""Publishability gate: fail if tracked text contains project or personal
identifiers.

The transferable tier's contract is zero project nouns, zero personal
data. Generic patterns (secrets, emails) live in scrub_terms.txt
(committed). Project-specific nouns live in scrub_terms.local.txt
(GITIGNORED — the term list itself would otherwise name the project in
the public tree).

Scans `git ls-files` (the publishable set) so gitignored local files are
excluded by construction. Files with a UTF-16/UTF-32 BOM are decoded and
scanned — NULs are structural there, not proof of binary; only NUL-bearing
files with no text BOM are skipped. Lines beyond MAX_LINE_CHARS are
truncated-scanned with a note (an unbounded line hands a pathological
pattern quadratic work). Exit 0 = clean; exit 1 with file:line:term hits;
exit 2 = the instrument itself failed (no terms, enumeration failed or
empty, nothing scannable, a term tier missing under
SCRUB_REQUIRE_LOCAL_TERMS, or a skipped file / truncated line under
SCRUB_REQUIRE_TOTAL_SCAN) — never reports clean on a collapsed
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
MAX_LINE_CHARS = 4096


def _env_flag(name: str) -> bool:
    # "" and "0" are the documented off-values (pinned by tests).
    return os.environ.get(name, "") not in ("", "0")


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


def decode_text(data: bytes) -> str | None:
    """Decode tracked bytes as text; None means binary (skip).

    BOM checks run before the NUL heuristic: NUL bytes are structural in
    UTF-16/UTF-32, and skipping those files let a planted secret ride
    through unscanned (2026-08-13 adversarial pass). UTF-32 is checked
    first — a UTF-32-LE BOM begins with the UTF-16-LE BOM bytes.
    """
    if data[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"):
        return data.decode("utf-32", "replace")
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", "replace")
    if b"\x00" in data[:8192]:
        return None
    return data.decode("utf-8", "replace")


def scan_text(name: str, text: str,
              patterns: list[re.Pattern[str]]) -> tuple[list[str], int]:
    """Return (hits, truncated_line_count) for one file's text.

    Lines beyond MAX_LINE_CHARS are scanned only up to the cap — an
    unbounded line hands a pathological pattern quadratic work (measured
    2026-08-13: 80 KB @-less line -> 35 s on the old email regex). The
    tail is NOT scanned; the caller reports the truncation.
    """
    hits = []
    truncated = 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > MAX_LINE_CHARS:
            line = line[:MAX_LINE_CHARS]
            truncated += 1
        for pat in patterns:
            m = pat.search(line)
            if m:
                hits.append(f"{name}:{lineno}: {m.group(0)!r}")
    return hits, truncated


def tracked_files() -> list[Path] | None:
    try:
        proc = subprocess.run(["git", "ls-files"], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return [ROOT / p for p in proc.stdout.splitlines() if p.strip()]


def main(argv: list[str]) -> int:
    # Consoles on this machine encode with the OEM codepage (cp949), not
    # UTF-8: the gate must never die encoding its own verdict.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    texts = []
    for f in TERM_FILES:
        if f.is_file():
            texts.append(f.read_text(encoding="utf-8"))
            continue
        if (f.name == LOCAL_TERMS_NAME
                and _env_flag("SCRUB_REQUIRE_LOCAL_TERMS")):
            print(f"scrub: {f.name} absent with SCRUB_REQUIRE_LOCAL_TERMS "
                  "set -- refusing to scan on the generic tier alone")
            return 2
        print(f"scrub: WARNING -- term tier {f.name} absent; its patterns "
              "are not being scanned for")
    patterns = load_terms(texts)
    if not patterns:
        print("scrub: no terms loaded -- refusing to report clean on an "
              "empty instrument (see prove-an-instrument-can-fail)")
        return 2
    files = tracked_files()
    if files is None:
        print("scrub: git ls-files failed -- cannot enumerate the "
              "publishable set (not a git repo, or git unavailable?)")
        return 2
    all_hits: list[str] = []
    notes: list[str] = []
    skipped_names: list[str] = []
    scanned = 0
    truncated = 0
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            data = path.read_bytes()
        except OSError:
            skipped_names.append(rel)
            continue
        text = decode_text(data)
        if text is None:
            skipped_names.append(rel)  # binary: NUL-bearing, no text BOM
            continue
        scanned += 1
        hits, clipped = scan_text(rel, text, patterns)
        all_hits.extend(hits)
        if clipped:
            truncated += clipped
            notes.append(f"scrub: NOTE -- {rel}: {clipped} line(s) too "
                         f"long, truncated-scan (first {MAX_LINE_CHARS} "
                         "chars of each scanned)")
    skipped = len(skipped_names)
    if not scanned:
        print(f"scrub: scanned 0 of {len(files)} tracked files "
              f"({skipped} skipped) -- refusing to report clean on an "
              "empty scan")
        return 2
    for note in notes:
        print(note)
    if all_hits:
        print(f"SCRUB FAILED: {len(all_hits)} hit(s) over {scanned} files:")
        for h in all_hits:
            print(f"  {h}")
        return 1
    if _env_flag("SCRUB_REQUIRE_TOTAL_SCAN") and (skipped or truncated):
        print(f"scrub: partial scan with SCRUB_REQUIRE_TOTAL_SCAN set -- "
              f"{skipped} file(s) skipped, {truncated} line(s) truncated "
              "-- refusing to report clean")
        for name in skipped_names:
            print(f"  skipped: {name}")
        return 2
    summary = (f"scrub clean: {scanned} tracked text files, "
               f"{len(patterns)} patterns, {skipped} skipped")
    if truncated:
        summary += f", {truncated} truncated line(s)"
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
