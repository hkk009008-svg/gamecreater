"""SessionStart orientation: what is true right now, measured, in one block.

Wired to the SessionStart hooks in .claude/settings.json and
.codex/hooks.json. Its stdout is injected into the session's context, so this
is the first thing a fresh session sees -- before it reads anything, before it
decides anything.

WHY IT EXISTS. AGENTS.md asks the agent to perform a short orientation
ritual by hand at every session start, and the checkpoint ritual by hand at
every hold. Both depend on the agent REMEMBERING. Measured failures of
exactly that dependency, all on 2026-08-13/14:

  - GAME.local.md:33 records "User's editor UI is Korean; match error
    strings by shape/position." A session still wrote a matcher against
    English pin names, lost a boot to it, and rediscovered the fact from a
    Korean error string. The knowledge was in the repo and never reached
    the moment it mattered.
  - memory/LESSONS.md certified "All 110 tests green, strict scrub clean"
    while the strict scrub exits 1 on two hits. A false green sat in the
    provenance the next distill reads.
  - The Antigravity guard failed open for 13 tool calls and nothing
    surfaced it; it was found by reading that harness's log by hand.
  - A push blocked through Bash executed through Monitor, because the
    matcher named two tools and the harness had three.

So this script does not re-state doctrine. It states MEASUREMENTS that
contradict assumptions, and it puts the loudest ones first. Anything it
cannot measure it says it cannot measure -- a blank where a number belongs
is the one output that must never look like a zero.

CONTRACT. Always exits 0. SessionStart cannot block and must not try: a
crash here would cost the session its orientation, which is the opposite of
the point. Every probe is individually guarded and degrades to a NOTE line.
No network (no `gh`), so it stays fast and works offline.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from game_config import load_game_config

ROOT = SCRIPTS.parent
TODAY = date.today()
WARN: list[str] = []
LINES: list[str] = []


def out(s: str = "") -> None:
    LINES.append(s)


def warn(s: str) -> None:
    WARN.append(s)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def git(args: list[str], cwd: Path) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                           text=True, timeout=8)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def days_since(d: str) -> int | None:
    for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
        try:
            return (TODAY - datetime.strptime(d, fmt).date()).days
        except ValueError:
            continue
    return None


def age_str(n: int | None) -> str:
    if n is None:
        return "age unknown"
    if n == 0:
        return "today"
    return f"{n}d old"


# --------------------------------------------------------------------------
# 1. the game binding
# --------------------------------------------------------------------------
def game_binding() -> dict:
    config = load_game_config(ROOT / "GAME.local.md")
    if not config.source.is_file():
        warn("GAME.local.md is MISSING - copy templates/GAME.local.template.md "
             "and confirm the paths with the user before doing anything.")
        return {}
    g = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in {
            "name": config.name,
            "slug": config.slug,
            "working": config.working_root,
            "project": config.project_root,
            "engine": config.engine_root,
            "now": config.now,
            "inbox": config.lessons,
        }.items()
        if value is not None
    }
    for k in ("working", "project", "engine"):
        if k in g and not Path(g[k]).exists():
            warn(f"{k} root {g[k]} does not exist on this machine")
    return g


# --------------------------------------------------------------------------
# 2. NOW.md -- the current-state file, and whether it is stale
# --------------------------------------------------------------------------
def now_block(g: dict) -> None:
    path = Path(g.get("now", "")) if g.get("now") else None
    if not path or not path.is_file():
        warn("NOW.md not found - a session that starts without it starts blind")
        return
    txt = read(path)
    mtime = date.fromtimestamp(path.stat().st_mtime)
    stated = re.search(r"\*\*As of:\*\*\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", txt)
    a_state = days_since(stated.group(1)) if stated else None
    a_file = (TODAY - mtime).days
    out(f"NOW.md  written {age_str(a_file)}"
        + (f", says 'as of' {stated.group(1)} ({age_str(a_state)})"
           if stated else ", NO 'As of:' line"))
    if a_state is not None and a_file is not None and abs(a_state - a_file) > 1:
        warn(f"NOW.md's 'As of:' date and its file mtime disagree by "
             f"{abs(a_state - a_file)}d - one of them is lying")

    # the two sections a fresh session cannot work without
    for head in ("Next executable action", "Active blockers"):
        m = re.search(rf"^#+\s*{re.escape(head)}\s*$(.*?)(?=^#+\s|\Z)",
                      txt, re.M | re.S)
        if not m:
            warn(f"NOW.md has no '{head}' section")
            continue
        body = [ln.rstrip() for ln in m.group(1).strip().splitlines() if ln.strip()]
        out(f"  {head}:")
        for ln in body[:4]:
            out(f"    {ln[:160]}")
        if len(body) > 4:
            out(f"    ... (+{len(body) - 4} more lines in NOW.md)")

    # the open register, counted by the tier heading it sits under
    tiers: dict[str, list[str]] = {}
    cur = None
    for ln in txt.splitlines():
        h = re.match(r"^###\s+(.*)$", ln)
        if h:
            cur = h.group(1).strip()
            continue
        item = re.match(r"^-\s+([A-Z]{2,}-[A-Z0-9]+-\d+)", ln)
        if item and cur:
            tiers.setdefault(cur, []).append(item.group(1))
    if tiers:
        out("  Open register:")
        for tier, ids in tiers.items():
            dupes = {i for i in ids if ids.count(i) > 1}
            extra = f"  [DUPLICATE: {', '.join(sorted(dupes))}]" if dupes else ""
            out(f"    {tier}: {len(ids)} - {', '.join(ids)}{extra}")
            if dupes:
                warn(f"register has duplicate id(s) {sorted(dupes)} under "
                     f"'{tier}' - one of them is unreachable")
    else:
        warn("no register items parsed out of NOW.md")


# --------------------------------------------------------------------------
# 3. lesson inboxes -- growth is the signal, not size
# --------------------------------------------------------------------------
def inbox_block(g: dict) -> None:
    def count(p: Path) -> tuple[int, str | None]:
        txt = read(p)
        if not txt:
            return (-1, None)
        n = len(re.findall(r"^-\s+20\d\d-\d\d-\d\d", txt, re.M))
        marks = re.findall(r"DISTILL MARKER\s+(20\d\d-\d\d-\d\d)", txt)
        return (n, marks[-1] if marks else None)

    rows = [("harness", ROOT / "memory" / "LESSONS.md")]
    if g.get("inbox"):
        rows.append((g.get("slug", "game"), Path(g["inbox"])))
    for label, p in rows:
        n, mark = count(p)
        if n < 0:
            warn(f"{label} lessons inbox unreadable at {p}")
            continue
        # Append-only verdict against the inbox's own committed HEAD. A
        # count survives a rewrite; the prefix check does not, and a session
        # that starts on a silently edited inbox trusts lessons that may no
        # longer be there.
        ao = ""
        try:
            import check_lessons_inbox as cli
            repo = p.parent
            probe = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=15)
            if probe.returncode == 0:
                verdict, detail, _ = cli.check_one(
                    Path(probe.stdout.strip()), p)
                ao = f", append-only {verdict}"
                if verdict == "VIOLATION":
                    warn(f"{label} inbox EDITED since HEAD - "
                         + detail.splitlines()[0]
                         + " (committed lessons changed; distill in "
                           "progress, or a lesson is dying)")
        except Exception as e:
            ao = f", append-only UNCHECKED({type(e).__name__})"
        since = days_since(mark) if mark else None
        out(f"Lessons/{label}: {n} entries"
            + (f", last distill {mark} ({age_str(since)})" if mark
               else ", NO distill marker") + ao)
        if mark is None and n > 10:
            warn(f"{label} inbox has {n} entries and no distill marker")


# --------------------------------------------------------------------------
# 4. repo state -- unpushed work is invisible until someone looks
# --------------------------------------------------------------------------
def repo_block(g: dict) -> None:
    repos = [("gamecreater", ROOT)]
    for k in ("working", "project"):
        if g.get(k):
            repos.append((Path(g[k]).name, Path(g[k])))
    for label, path in repos:
        if not (path / ".git").exists():
            continue
        branch = git(["rev-parse", "--abbrev-ref", "HEAD"], path) or "?"
        counts = git(["rev-list", "--left-right", "--count",
                      f"origin/{branch}...HEAD"], path)
        ahead = behind = None
        if counts and "\t" in counts:
            behind, ahead = (int(x) for x in counts.split("\t")[:2])
        dirty = len([ln for ln in git(
            ["status", "--porcelain", "--untracked-files=all"], path
        ).splitlines() if ln.strip()])
        bits = [f"{label}@{branch}"]
        if ahead:
            bits.append(f"{ahead} UNPUSHED")
        if behind:
            bits.append(f"{behind} behind")
        if dirty:
            bits.append(f"{dirty} dirty")
        if not ahead and not behind and not dirty:
            bits.append("clean, in sync")
        out("  " + "  ".join(bits))
        if ahead:
            warn(f"{label} has {ahead} unpushed commit(s) - the work exists "
                 f"on one disk only")


# --------------------------------------------------------------------------
# 5. guard health -- a guard that is not running is not a guard
# --------------------------------------------------------------------------
def guard_block() -> None:
    codex = ROOT / ".codex" / "hooks.json"
    try:
        data = json.loads(read(codex))
        hooks = data.get("hooks", {})
        pre = hooks.get("PreToolUse", [])
        start = hooks.get("SessionStart", [])
        matcher = "|".join(str(entry.get("matcher") or "") for entry in pre)
        commands = "\n".join(
            str(hook.get("commandWindows") or hook.get("command") or "")
            for entries in (pre, start)
            for entry in entries
            for hook in entry.get("hooks", []))
        out(f"Codex hook file: PreToolUse={matcher or 'MISSING'}; "
            f"SessionStart={'configured' if start else 'MISSING'}; "
            "trust/running state not observable here")
        if "Bash" not in matcher or "hook_pretooluse.py" not in commands:
            warn("Codex PreToolUse is not wired to the repository guard")
        if not start or "session_start.py" not in commands:
            warn("Codex SessionStart is not wired to session orientation")
    except Exception as e:                                      # noqa: BLE001
        warn(f"could not read .codex/hooks.json: {e}")

    s = ROOT / ".claude" / "settings.json"
    try:
        data = json.loads(read(s))
        matched: set[str] = set()
        for entry in data.get("hooks", {}).get("PreToolUse", []):
            matched.update(p.strip() for p in (entry.get("matcher") or "").split("|"))
        missing = [t for t in ("Bash", "PowerShell", "Monitor") if t not in matched]
        out(f"Guards: PreToolUse matches {sorted(x for x in matched if x)}")
        if missing:
            warn(f"PreToolUse does NOT match {missing} - those tools can run "
                 f"shell commands past both mechanized rules")
    except Exception as e:                                      # noqa: BLE001
        warn(f"could not read .claude/settings.json: {e}")

    h = ROOT / ".agents" / "hooks.json"
    if h.is_file():
        try:
            data = json.loads(read(h))
            for group in data.values():
                for entry in group.get("PreToolUse", []):
                    for hook in entry.get("hooks") or []:
                        rel = hook.get("command", "").split()[-1].strip('"')
                        if not (h.parent / rel).resolve().is_file():
                            warn(f"Antigravity hook path {rel!r} does not "
                                 f"resolve from {h.parent} - that harness's "
                                 f"guard fails OPEN")
        except Exception as e:                                  # noqa: BLE001
            warn(f"could not read .agents/hooks.json: {e}")


# --------------------------------------------------------------------------
# 5b. engine state -- an open editor blocks every headless launch
# --------------------------------------------------------------------------
def engine_block() -> None:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import engine_run                                         # noqa: PLC0415
        m = engine_run.read_mode()
    except Exception as e:                                        # noqa: BLE001
        warn(f"could not read engine mode: {e}")
        return
    ed = {True: "editor running", False: "no editor",
          None: "COULD NOT ENUMERATE"}[m.editor_running]
    out(f"Engine: {m.name} mode ({ed})")
    if m.editor_running:
        warn("an editor is open, so EVERY headless capture, probe and sweep is "
             "blocked; use OpenClaw for live-editor work or close the editor")
    elif m.editor_running is None:
        warn("editor process state is unknown, so headless launches fail closed")


# --------------------------------------------------------------------------
# 6. skill surface -- both mirrors are gitignored, so drift is invisible
# --------------------------------------------------------------------------
def skills_block() -> None:
    import sync_skills                                      # noqa: PLC0415
    desired = sync_skills.desired_mirror()
    counts = {}
    problems = []
    for surface in sync_skills.SURFACES:
        name = surface.parent.name.lstrip(".")
        counts[name] = len(sync_skills.current_surface(surface))
        problems.extend(
            f"{name}: {p}" for p in sync_skills.drift(
                desired, sync_skills.current_surface(surface)))
    out(f"Skills: {len(desired)} active, mirrored " +
        ", ".join(f"{k}={v}" for k, v in counts.items()))
    if problems:
        warn("skill discovery surface drift - run python scripts/sync_skills.py; "
             + "; ".join(problems[:4]))

    names = {p.parent.name for p in (ROOT / "skills").glob("*/*/SKILL.md")}
    router = read(ROOT / "AGENTS.md")
    unrouted = sorted(n for n in names if n not in router)
    if unrouted:
        warn(f"AGENTS.md routes {len(names) - len(unrouted)} of {len(names)} "
             f"skills; unrouted: {', '.join(unrouted)}")


def main() -> int:
    # This console is cp949 (Korean Windows). NOW.md and the lesson inboxes
    # are full of em dashes, and this script echoes their lines verbatim, so
    # printing raw kills it with UnicodeEncodeError -- which it did on the
    # first run, at position 359. scripts/scrub_check.py already carries this
    # exact fix; the lesson existed and did not reach the new script. That is
    # the same routing failure this file was written to attack.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    g = game_binding()
    out("=== SESSION ORIENTATION (measured, not recalled) ===")
    if g:
        out(f"Game: {g.get('name', '?')} [{g.get('slug', '?')}]  "
            f"working={g.get('working', '?')}  project={g.get('project', '?')}")
    out()
    now_block(g)
    out()
    inbox_block(g)
    out()
    out("Repos:")
    repo_block(g)
    out()
    guard_block()
    engine_block()
    skills_block()
    if WARN:
        out()
        out(f"--- {len(WARN)} THING(S) THAT CONTRADICT THE DEFAULT ASSUMPTION ---")
        for w in WARN:
            out(f"  ! {w}")
    out()
    out("Skills are the default, not an option. Authorization boundary in "
        "AGENTS.md is per-act: push, merge, DCC launch, canonical Content "
        "writes, publishing, deletions.")
    print("\n".join(LINES))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                                      # noqa: BLE001
        # Orientation must never cost the session its start.
        print(f"[session_start degraded: {type(e).__name__}: {e}]")
        sys.exit(0)
