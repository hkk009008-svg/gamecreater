"""Classify a finished engine run into two independent verdicts.

    python scripts/run_verdict.py <log> [--artifact P]... [--exit-code N]

WHY TWO VERDICTS. `separate-execution-from-output` says a run must answer
two questions that a single status field cannot: did the process run to
completion (EXECUTION), and is the artifact it was supposed to produce
actually there (OUTPUT). This module refuses to collapse them, and refuses
to let a script-authored sentinel stand in for either.

CALIBRATED, not guessed. Every rule below was measured against the 2,283
`.log` files under D:/Kurogane and D:/Unreal on 2026-08-14. The three
findings that shaped it:

  1. A CRASHED RUN'S LAST LINE READS CLEAN. 176 of 211 logs carrying a
     crash signature end on `LogCore: Engine exit requested (reason: Win
     RequestExit...)` -- the same line a healthy shutdown writes. Zero of
     the 211 also contain `Log file closed`. So: scan the BODY for the
     crash marker; a last-line check is a broken instrument here.

  2. THE SENTINEL AND THE ENGINE DISAGREE, OFTEN. 328 engine logs carry a
     `=PASS`-shaped sentinel and never closed cleanly; 124 carry one
     alongside a crash signature. The script printed PASS and the engine
     died in the same run. `sentinel_claims_pass` is therefore reported as
     its own field, never folded into EXECUTION, and a disagreement is
     surfaced as `contradiction`.

  3. 238 FILES IN THE CORPUS ARE NOT ENGINE LOGS AT ALL (Blender, shasum,
     port listeners). Classifying those on engine rules would invent
     verdicts. `NOT_AN_ENGINE_LOG` is a refusal, and a refusal is a better
     answer than a confident wrong one.

EXECUTION is one of:
    COMPLETE          engine wrote `Log file closed` and no crash marker
    CRASHED           a crash marker appears anywhere in the body
    KILLED_STALL      supervisor killed it: log stopped growing
    KILLED_TIMEOUT    supervisor killed it: wall-clock budget exhausted
    RUNNING           process still alive, nothing terminal in the log
    TRUNCATED         engine log, no crash, no clean close -- it just stops
    EMPTY             file exists but the engine never got going
    NO_LOG            the declared log path does not exist
    NOT_AN_ENGINE_LOG refused: no engine log categories found

OUTPUT is one of:
    PRESENT              every declared artifact exists, is non-empty, and
                         does not self-report failure
    MISSING              at least one declared artifact is absent or 0 bytes
    PRESENT_BUT_FAILING  the artifact landed and says it failed
    PRESENT_BUT_IDENTICAL  several artifacts were declared and they are
                         byte-identical -- the run varied nothing
    UNDECLARED           the caller named no artifact -- this run gates on
                         nothing

PRESENT_BUT_FAILING exists because the first real run through this module's
supervisor scored EXECUTION=COMPLETE, OUTPUT=PRESENT, CITABLE=yes over a
report whose own first line was `"status": "FAIL"`. "The file exists" is a
weaker claim than "the run produced a result", and collapsing them
reintroduces exactly the failure this module was written to stop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# --- Measured constants ------------------------------------------------

# Any of these anywhere in the body means the engine died, regardless of how
# tidily the log ends. See finding (1) in the module docstring.
CRASH_RE = re.compile(
    r"(Fatal error|Assertion failed|Access violation"
    r"|=== Critical error|LowLevelFatalError|EXCEPTION_ACCESS_VIOLATION"
    r"|Unhandled Exception)",
    re.IGNORECASE,
)

# The engine's own end-of-file marker. Present in 1,375 of 2,283 corpus logs
# and in none of the 211 that crashed.
CLEAN_CLOSE = "Log file closed"

# Engine log lines are `LogCategory: ...`. Requiring several distinct
# categories keeps a stray "Log file closed" inside some other tool's output
# from being read as an engine run.
LOG_CATEGORY_RE = re.compile(r"^\s*(?:\[[^\]]*\]\s*)*(Log[A-Za-z0-9_]+):", re.MULTILINE)
MIN_LOG_CATEGORIES = 3

# 193 corpus logs are under 2 KB; the smallest is 48 bytes. That shape is the
# mangled-`-abslog` failure from `render-a-headless-capture`: the editor
# launches, exits at once, and writes essentially nothing.
EMPTY_MAX_BYTES = 2048

# The RHI the engine actually chose, from the log -- which is authoritative.
# The obvious in-process route is not: `r.RHI.Name` returns "" under
# UE 5.8.1, so a probe asserting on that cvar reports rhi_matches=False on a
# perfectly healthy D3D12 run. A check that always says no is worse than no
# check, because it looks like a finding.
RHI_RE = re.compile(
    r"^LogRHI:\s*(?:Using Default RHI:\s*(\S+)"
    r"|RHI (\S+) with Feature Level \S+ is supported and will be used)",
    re.MULTILINE)

# Script-authored success sentinels. `KUROGANE_MH_CAPTURE=PASS` has fired
# over black frames, over a bald character, and over two renders that changed
# exactly 0 px. It is evidence about the script, not about the engine.
SENTINEL_RE = re.compile(r"\b[A-Z][A-Z0-9_]{3,}=(PASS|COMPLETE|OK)\b")

TERMINAL_KILLS = {"stall": "KILLED_STALL", "timeout": "KILLED_TIMEOUT"}


@dataclass
class Verdict:
    execution: str
    output: str
    sentinel_claims_pass: bool
    contradiction: bool
    environment_ok: bool = True
    reasons: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["citable"] = self.citable
        return d

    @property
    def execution_ok(self) -> bool:
        return self.execution == "COMPLETE"

    @property
    def citable(self) -> bool:
        """A run you may quote a result from: engine finished, artifact
        landed and did not self-report failure, and the environment was the
        one you asked for. UNDECLARED is not citable -- a run gating on
        nothing has not demonstrated it produced anything."""
        return (self.execution == "COMPLETE"
                and self.output == "PRESENT"
                and self.environment_ok)


def extract_rhi(text: str) -> str | None:
    """Which RHI the engine actually initialised, or None if the log never
    said. None is not 'no RHI' -- a truncated log also never says."""
    m = RHI_RE.search(text)
    if not m:
        return None
    return m.group(1) or m.group(2)


def is_engine_log(text: str) -> bool:
    """True when the text carries at least MIN_LOG_CATEGORIES distinct
    engine log categories. Distinct, not total: a file repeating one
    category is likelier a filtered excerpt than a real run."""
    return len(set(LOG_CATEGORY_RE.findall(text))) >= MIN_LOG_CATEGORIES


def classify_log(
    text: str,
    *,
    size_bytes: int,
    process_alive: bool = False,
    killed: str | None = None,
) -> tuple[str, list[str]]:
    """Pure core: text in, EXECUTION verdict + reasons out.

    `killed` is a supervisor fact ('stall' | 'timeout' | None), not something
    readable from the log. A crash marker still wins over it: "we killed a
    process that had already crashed" is the more specific truth.
    """
    reasons: list[str] = []

    if size_bytes == 0:
        return "EMPTY", ["log file is zero bytes"]

    if not is_engine_log(text):
        if size_bytes <= EMPTY_MAX_BYTES:
            return "EMPTY", [
                f"{size_bytes} B and no engine log categories -- the engine "
                f"never started. Classic mangled -abslog argument."
            ]
        return "NOT_AN_ENGINE_LOG", [
            f"fewer than {MIN_LOG_CATEGORIES} distinct 'LogX:' categories in "
            f"{size_bytes} B; refusing to apply engine rules to it"
        ]

    crash = CRASH_RE.search(text)
    if crash:
        reasons.append(f"crash marker {crash.group(1)!r} at byte {crash.start()}")
        if killed:
            reasons.append(f"supervisor also killed it ({killed}); crash is the "
                           f"more specific cause")
        if CLEAN_CLOSE not in text:
            tail = text.rstrip().rsplit("\n", 1)[-1][:80]
            reasons.append(f"last line reads {tail!r} -- clean-looking last "
                           f"lines are normal for crashes here (176/211)")
        return "CRASHED", reasons

    if CLEAN_CLOSE in text:
        if killed:
            # Rare but real: killed after the engine had already closed its log.
            reasons.append(f"{CLEAN_CLOSE!r} present although supervisor "
                           f"recorded a {killed} kill")
            return "COMPLETE", reasons
        return "COMPLETE", [f"{CLEAN_CLOSE!r} present, no crash marker"]

    if killed:
        return TERMINAL_KILLS[killed], [
            f"supervisor killed the process ({killed}); engine never wrote "
            f"{CLEAN_CLOSE!r}"
        ]

    if process_alive:
        return "RUNNING", ["process still alive; no terminal marker yet"]

    return "TRUNCATED", [
        f"engine log with no crash marker and no {CLEAN_CLOSE!r}. The process "
        f"is gone and the engine never shut down -- 670 of 2,045 corpus "
        f"engine logs look like this, and 328 of those still print a PASS."
    ]


# Values a report's own status field uses to say it did not succeed. A
# report claiming INCONCLUSIVE is also not a result: `render-a-headless-
# capture` requires a run whose readiness predicate never went true to
# report INCONCLUSIVE rather than PASS, so honouring that is the point.
FAILING_STATUS = {"fail", "failed", "failure", "error", "inconclusive"}


def self_reported_failure(path: Path) -> str | None:
    """Read a JSON artifact's own verdict. Returns a reason, or None.

    Deliberately narrow: only an explicit `status` in FAILING_STATUS, a
    truthy `error`, or a non-empty `errors` counts. `"error": null` and
    `"errors": []` are how healthy reports say nothing went wrong, and
    treating those as failures would make the gate unusable and get it
    switched off.
    """
    if path.suffix.lower() != ".json":
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError) as e:
        return f"declared a .json artifact that does not parse: {e}"
    if not isinstance(data, dict):
        return None
    status = data.get("status")
    if isinstance(status, str) and status.strip().lower() in FAILING_STATUS:
        return f'report self-reports status={status!r}'
    err = data.get("error")
    if err:
        return f"report carries a non-empty 'error': {str(err).splitlines()[0][:120]}"
    errs = data.get("errors")
    if isinstance(errs, (list, tuple)) and len(errs):
        return f"report carries {len(errs)} entry/entries in 'errors'"
    return None


def identical_groups(artifacts: list[Path]) -> list[list[Path]]:
    """Groups of 2+ declared artifacts with identical bytes.

    Only meaningful when the caller declared MORE THAN ONE artifact: a single
    artifact cannot be a duplicate of anything, and two runs legitimately
    producing the same file is a different question from one run producing
    the same file N times.

    There is deliberately no `len(artifacts) < 2` fast path. One was written
    here and mutation testing found it VACUOUS -- deleting it broke no test,
    because the `len(g) > 1` filter below already returns nothing for a lone
    artifact. A guard that cannot fail is not a safeguard, it is a second
    place for the rule to drift away from the first.
    """
    by_hash: dict[str, list[Path]] = {}
    for a in artifacts:
        try:
            h = hashlib.sha256(a.read_bytes()).hexdigest()
        except OSError:
            continue
        by_hash.setdefault(h, []).append(a)
    return [g for g in by_hash.values() if len(g) > 1]


def check_artifacts(artifacts: list[Path]) -> tuple[str, list[str], list[dict]]:
    if not artifacts:
        return "UNDECLARED", [
            "no artifact declared; this run gates on nothing. "
            "Exit code 0 with no artifact is not a pass."
        ], []
    detail, missing, failing = [], [], []
    for a in artifacts:
        try:
            size = a.stat().st_size if a.exists() else None
        except OSError as e:                       # permissions, bad path
            size = None
            detail.append({"path": str(a), "bytes": None, "error": str(e)})
            missing.append(f"{a} (stat failed: {e})")
            continue
        entry = {"path": str(a), "bytes": size}
        detail.append(entry)
        if size is None:
            missing.append(f"{a} (absent)")
            continue
        if size == 0:
            missing.append(f"{a} (zero bytes)")
            continue
        why = self_reported_failure(a)
        if why:
            entry["self_reported_failure"] = why
            failing.append(f"{a}: {why}")

    if missing:
        return "MISSING", [f"declared artifact not usable: {m}" for m in missing], detail
    if failing:
        return "PRESENT_BUT_FAILING", [
            f"artifact landed but says it FAILED -- {f}. 'The file exists' is "
            f"a weaker claim than 'the run produced a result'." for f in failing
        ], detail

    # A sweep that did not sweep. Measured 2026-08-14: a 7-variant tone sweep
    # wrote seven BYTE-IDENTICAL files and scored PRESENT, because existence,
    # non-emptiness and a PASS report were all true. This project's own skill
    # corpus already records the ancestor of this failure -- "two full renders
    # that changed exactly 0 px, twice". Declaring N artifacts asserts N
    # distinct results; if they are identical, say so.
    dupes = identical_groups(artifacts)
    if dupes:
        biggest = max(dupes, key=len)
        return "PRESENT_BUT_IDENTICAL", [
            f"{len(biggest)} of {len(artifacts)} declared artifacts are "
            f"BYTE-IDENTICAL: {', '.join(p.name for p in biggest)}. Declaring "
            f"several artifacts asserts several results. Identical bytes mean "
            f"the run varied nothing -- the thing you were sweeping never "
            f"reached the output."
        ], detail

    return "PRESENT", [f"all {len(artifacts)} declared artifact(s) present, "
                       f"non-empty, distinct, and not self-reporting failure"], detail


def read_log(path: Path) -> tuple[str | None, int]:
    """Decode permissively. The corpus contains cp949 Korean text inside
    otherwise-UTF-8 logs; a decode error must not become a verdict."""
    if not path.is_file():
        return None, 0
    raw = path.read_bytes()
    return raw.decode("utf-8", "replace"), len(raw)


def verdict_for(
    log_path: Path,
    artifacts: list[Path] | None = None,
    *,
    exit_code: int | None = None,
    process_alive: bool = False,
    killed: str | None = None,
    expect_rhi: str | None = None,
) -> Verdict:
    artifacts = artifacts or []
    text, size = read_log(log_path)

    rhi = None
    environment_ok = True
    if text is None:
        execution, reasons = "NO_LOG", [f"no log at declared path {log_path}"]
        sentinel = False
    else:
        execution, reasons = classify_log(
            text, size_bytes=size, process_alive=process_alive, killed=killed)
        sentinel = bool(SENTINEL_RE.search(text))
        rhi = extract_rhi(text)

    if expect_rhi:
        # Positive assertion: the RHI you expected is PRESENT. Asserting only
        # that "NullRHI" is absent passes on a truncated log too.
        if rhi is None:
            environment_ok = False
            reasons.append(
                f"expected RHI {expect_rhi!r} but the log never says which "
                f"RHI initialised. Absence of the string is also what a "
                f"truncated log looks like, so this is not a pass.")
        elif rhi.lower() != expect_rhi.lower():
            environment_ok = False
            reasons.append(f"RHI mismatch: expected {expect_rhi!r}, engine "
                           f"initialised {rhi!r}")
        else:
            reasons.append(f"RHI {rhi!r} confirmed present in the log")

    output, out_reasons, detail = check_artifacts(artifacts)
    reasons += out_reasons

    contradiction = sentinel and execution != "COMPLETE"
    if contradiction:
        reasons.append(
            f"CONTRADICTION: the script printed a success sentinel but "
            f"EXECUTION is {execution}. Measured on this corpus: 328 engine "
            f"logs claim PASS without closing cleanly, 124 claim PASS with a "
            f"crash marker in the same run. Believe the engine."
        )

    if exit_code not in (None, 0):
        reasons.append(
            f"exit code {exit_code}"
            + (" (large negative -> access violation, i.e. a crash, not a "
               "script failure)" if exit_code < -1000 else "")
            + " -- recorded, but NOT used as a gate: commandlets have a "
              "history of not propagating failure codes."
        )

    return Verdict(
        execution=execution,
        output=output,
        sentinel_claims_pass=sentinel,
        contradiction=contradiction,
        environment_ok=environment_ok,
        reasons=reasons,
        evidence={
            "log": str(log_path),
            "log_bytes": size,
            "exit_code": exit_code,
            "killed": killed,
            "process_alive": process_alive,
            "rhi": rhi,
            "rhi_expected": expect_rhi,
            "artifacts": detail,
        },
    )


def render(v: Verdict) -> str:
    lines = [
        f"EXECUTION : {v.execution}",
        f"OUTPUT    : {v.output}",
        f"SENTINEL  : {'claims success' if v.sentinel_claims_pass else 'none found'}"
        + ("   <-- DISAGREES WITH THE ENGINE" if v.contradiction else ""),
        f"ENV       : RHI={v.evidence.get('rhi') or 'unstated'}"
        + ("" if v.environment_ok else "   <-- NOT THE ENVIRONMENT REQUESTED"),
        f"CITABLE   : {'yes' if v.citable else 'NO'}",
        "",
    ]
    lines += [f"  - {r}" for r in v.reasons]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("log", type=Path)
    ap.add_argument("--artifact", type=Path, action="append", default=[],
                    help="path the run was supposed to write; repeatable")
    ap.add_argument("--exit-code", type=int, default=None)
    ap.add_argument("--killed", choices=sorted(TERMINAL_KILLS), default=None)
    ap.add_argument("--expect-rhi", default=None,
                    help="assert this RHI initialised, e.g. D3D12")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv[1:])

    v = verdict_for(a.log, a.artifact, exit_code=a.exit_code, killed=a.killed,
                    expect_rhi=a.expect_rhi)
    print(json.dumps(v.as_dict(), indent=2) if a.json else render(v))
    # 0 citable, 1 ran-but-not-citable, 2 did not run cleanly.
    return 0 if v.citable else (1 if v.execution == "COMPLETE" else 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
