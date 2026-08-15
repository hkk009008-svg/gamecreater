# gamecreater — session router

This repo is the operating system for long-horizon game work: the session
anchor, the memory spine, the skill corpus, and the guard rails. The game
itself lives in its own repos, named by `GAME.local.md`. This file routes;
it does not teach. Lessons live in skills, current truth lives in the game's
`NOW.md`, and duplicating either here is a defect.

## Session start — load in this order, then work

1. Standing corrections load automatically from the harness memory index.
2. Read `GAME.local.md` — the active game's roots, engine, and repos. If it
   is missing, copy `templates/GAME.local.template.md` and ask the user to
   confirm the paths.
3. Build the skill discovery surface: `python3 scripts/sync_skills.py` (or
   `python` where that name exists). Canonical bodies live in `skills/`;
   `.claude/skills/` is generated and gitignored, so a fresh checkout has
   no discoverable surface until this runs.
4. Read the active game's `NOW.md` (path named in `GAME.local.md`) — the
   current arc, open register, blockers, and the next executable action.

That is the whole orientation. Do not re-derive state from chat memory when
`NOW.md` exists; if `NOW.md` contradicts the code or the assets, current
state wins and `NOW.md` gets corrected in the same session.

## Work from skills. Default, not an option.

Check `skills/<tier>/<name>/` (canonical) for a skill covering the work
and follow it. `.claude/skills/` is the generated copy the harness
auto-discovers; do not edit it by hand. Each skill was paid for by a real
failure; its Provenance section names which. Current code wins when a
skill drifts: record the conflict in the lessons inbox, do not silently
work around it.

**Before you launch or write anything**
`render-a-headless-capture` · `write-a-run-sidecar` ·
`back-up-before-a-destructive-write` · `derive-a-constant-from-the-asset` ·
`edit-vendor-data-headlessly`

**Before you believe a result**
`separate-execution-from-output` · `establish-a-noise-floor` ·
`prove-an-instrument-can-fail` · `judge-a-silhouette` ·
`verify-on-the-real-entry`

**When something works here and fails there**
`isolate-a-variable` · `watch-the-live-session` · `probe-a-claim` ·
`prove-a-control`

**At boundaries**
`pin-a-content-boundary` · `verify-a-cooked-package` ·
`create-regression-pin` · `checkpoint-a-hold` · `distill-an-arc`

**Engine and asset work**
`inspect-and-patch-blueprint-graph` · `audit-animation-montage-pipeline` ·
`pin-collision-and-trace-matrix` · `bridge-dcc-asset-roundtrip` ·
`triage-engine-crash-dump`

**Handing work outward**
`orchestrate-user-playtest` · `publish-a-repo`

Game-specific skills mirror in as `game-<name>-*`; they bind tighter than
the general skill when both apply.

Every canonical skill is routed above. `scripts/session_start.py` asserts
that at session start and names any skill this file has stopped mentioning
— seven were unrouted and therefore invisible until 2026-08-14, including
`triage-engine-crash-dump` while 300 crash dumps sat unread on disk.

## Authorization boundary

Standing, no further ask (confirm the exact grants in `GAME.local.md`):
read anything under the named roots; launch the engine headlessly for
captures, probes, and sweeps; write scripts, renders, logs, and docs inside
the working root; `git add` and `git commit` there.

Separately authorized by the user, each for the exact effect, executor, and
target — a work mode, a plan, or "let's resume" supplies none of them:

- any DCC tool launch (Blender or otherwise) — the engine grant never
  covers it
- writing canonical game content
- `git push` · `git merge` — separate acts; neither follows from a commit
- making any repo public, or publishing anything outward
- any paid or provider tool, including launching another agent
- deleting or overwriting an existing asset, render, or evidence file

Guards mechanize the two rules that were violated most expensively: pushes
are blocked unless the repo is verified private (or granted in
`public-grant.txt`), and headless engine launches are blocked while an
editor is open. Hooks live in `.claude/settings.json`; a block names the
rule and the override path. Do not bypass a guard silently — surface it.

The PreToolUse matcher is an **allowlist of tool names**, so a new
command-running tool arrives unguarded by default: `Monitor` was added
2026-08-14 after a measured bypass. MCP calls carry no shell command at
all, so a name-keyed rule blocks `mcp__*` tools naming a reserved act
(push, merge, publish, visibility). Add any new such tool to the matcher
*and* to `tests/test_settings_matcher.py`.

## Two engine modes, mutually exclusive

`HEADLESS` (default, no editor) runs captures, probes and sweeps.
`MCP` holds one editor open serving Unreal's MCP tools on
`127.0.0.1:8000/mcp`. They cannot overlap — the never-concurrent-editors
rule blocks a headless launch whenever any editor is running. Declare the
mode with `python scripts/mcp_session.py on|off|status` so the collision
reports itself as a stated choice instead of a broken guard; the guard's
verdict is unchanged either way. Client config: `.mcp.json`.

**`scripts/engine_run.py` is the entry point for both.** Do not hand-write
an `UnrealEditor-Cmd` line; the builder emits it from declared intent and
refuses at build time what a log scan can only diagnose afterwards.

    python scripts/engine_run.py mode         # which mode, and how to switch
    python scripts/engine_run.py mcp-check    # is MCP actually reachable
    python scripts/engine_run.py headless S.py --needs-rhi --artifact R.json

`mcp-check` proves the endpoint **speaks MCP** by completing a real
handshake, not merely that a port is open — a listener is not a protocol. It
reports reachability and mode-declaration separately: declaring the mode
protects the next session from killing a deliberate editor and has no
bearing on whether calls connect. Verified live 2026-08-14: protocol
`2025-06-18`, **71 toolsets** behind the three tool-search entry points.

`scripts/mcp_client.py` talks to the editor without a client restart —
`.mcp.json` is read at CLIENT STARTUP, so a session that just enabled MCP
cannot use the server it configured. Three things to know before debugging
your own arguments:

- **Every parameter is effectively required**, whatever `inputSchema.required`
  says. `CaptureViewport` advertises none, documents `captureTransform` as
  optional, then rejects `{}` — and rejects again on `annotations`.
- **Images arrive JSON-wrapped in a `text` block**, not an MCP `image` block.
  A client handling only `type == "image"` reports "no image" for a call
  that worked.
- **Never pass a `/Game/...` path through the Bash tool** — MSYS rewrites it
  to `C:/Program Files/Git/Game/...` and the tool answers "Asset not found".
  Set `MSYS_NO_PATHCONV=1` or use PowerShell.

An MCP call is not a lesser act than a Python one: canonical `Content/`
writes, deletions and publishing stay per-act authorized whichever transport
reaches them.

Every supervised run is watched by two independent timers — a log-stall
detector and a wall clock, because neither alone can tell a hung run from a
slow one — and ends in a `run_verdict` classification plus a sidecar. It
kills the whole process tree, not just the parent: orphaned
ShaderCompileWorkers read as a phantom "editor already running" on the next
launch.

## Never quote a run that is not CITABLE

`scripts/run_verdict.py` answers two questions a single status field
cannot, and refuses to merge them: **EXECUTION** (did the engine finish) and
**OUTPUT** (did the artifact land and not self-report failure). Measured
across the 2,283 `.log` files under `D:/Kurogane` and `D:/Unreal` on
2026-08-14:

| | |
|---|---|
| engine logs that never wrote `Log file closed` | 670 of 2,045 |
| crashed logs whose LAST LINE still reads clean | 176 of 211 |
| runs printing `=PASS` that the engine's own log contradicts | **396** |

So: a crash is found by scanning the body, never the tail. A script's
`=PASS` is evidence about the script and nothing else — it is reported as
its own field, and a disagreement surfaces as `contradiction`. A `.json`
artifact that exists but says `"status": "FAIL"` is `PRESENT_BUT_FAILING`,
not `PRESENT` — that state exists because the first real run through this
supervisor scored CITABLE over exactly such a report. `--needs-rhi` asserts
the RHI **positively** from the log, since absence of `NullRHI` is also what
a truncated log looks like.

## Work modes, one paragraph

Ordinary reversible work declares nothing. A long campaign is `explore`:
one arc brief (`memory/ARC-BRIEF.template.md`), recorded attempts, failures
kept, provisional claims. Freezing one candidate for acceptance is
`validate`. Touching canonical or live state is `promote`: rollback point
first, separate exact authority for the write. A mode never grants
authority.

## The improvement loop

During work, lessons append to the lessons inbox (`memory/LESSONS.md` for
harness-general lessons, the game's own inbox for game-specific ones) —
autonomously, at the moment they are paid for. Skill bodies change only at
arc end via `distill-an-arc`, on the user's go. Every skill edit updates
its Changelog with the evidence that forced it.

## Checkpoint ritual

Before claiming a safe hold, ending an arc, or any "commit push":
`checkpoint-a-hold` — update `NOW.md` and the register, sweep loose lessons
into the inbox, commit. A hold without a current `NOW.md` is not safe; the
next session starts blind exactly there.
