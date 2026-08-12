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
3. Read the active game's `NOW.md` (path named in `GAME.local.md`) — the
   current arc, open register, blockers, and the next executable action.

That is the whole orientation. Do not re-derive state from chat memory when
`NOW.md` exists; if `NOW.md` contradicts the code or the assets, current
state wins and `NOW.md` gets corrected in the same session.

## Work from skills. Default, not an option.

Check `.claude/skills/` for a skill covering the work and follow it. Each
one was paid for by a real failure; its Provenance section names which.
Current code wins when a skill drifts: record the conflict in the lessons
inbox, do not silently work around it.

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

Game-specific skills mirror in as `game-<name>-*`; they bind tighter than
the general skill when both apply.

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
