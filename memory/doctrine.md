# Memory doctrine — four tiers, each with one job

The system assumes every session starts with amnesia about everything not
written down. Each tier exists because a specific kind of forgetting was
paid for.

## Tier 1 — standing corrections (harness auto-memory)

Where: the harness's per-project memory directory; its index loads
automatically at session start.
What: durable corrections to *how I work* — verification discipline,
effort allocation, evidence standards. Not project facts, not task state.
Written: the moment the user corrects something, or a mistake's root cause
is a work-habit. One fact per file, linked liberally.
Failure it prevents: repeating a corrected behavior in a later session
that never saw the correction.

## Tier 2 — current truth (`NOW.md`, one per game)

Where: the game's working root, versioned.
What: the current arc and objective, the open register (tiered by what
each item blocks), active blockers, and the single next executable action.
Written: at every checkpoint — mandatory before any safe hold, arc end, or
push. Read: at every session start, before any work.
Rule inherited from hard experience: task state is never stored in
semantic memory or trusted from chat recall — it is read fresh from this
file and reconciled against the actual code/assets, which win.
Failure it prevents: the blind session start, and the stale-claim cascade
where work resumes against last week's reality.

## Tier 3 — lessons inbox (append-only, versioned)

Where: `memory/LESSONS.md` here for harness-general lessons; each game
keeps its own inbox for game-specific ones.
What: raw lessons at the moment they are paid for — one entry: date, what
happened, evidence ref, the rule it suggests, candidate skill target.
Written: autonomously, during work, without ceremony. Entries are cheap;
losing one is not.
Failure it prevents: lessons dying in gitignored notes, chat scrollback,
or "I'll remember that" — the exact leak that motivated this repo.

## Tier 4 — skills (distilled procedure)

Where: `skills/`, mirrored to the discovery surface by `sync_skills.py`.
What: the generalized procedure, its Provenance (which failure paid for
it), and its Changelog.
Written: only at arc-end distill (`distill-an-arc`), on the user's go —
never mid-task, never merely because a lesson arose. This is the sediment
guard: an inbox full of raw lessons costs nothing; a skill corpus full of
half-digested ones costs trust in every skill.
Failure it prevents: both staleness (skills lagging reality) and sediment
(reflexive skill edits degrading the corpus).

## The checkpoint ritual (binds tiers 2 and 3)

Before claiming a safe hold, ending an arc, or any push:

1. Update `NOW.md`: arc state, register, blockers, next executable action.
2. Sweep loose lessons from the session into the inbox(es).
3. Commit both with the work they describe.

A hold that skips this is not safe — the next session starts blind at
exactly the point where context was richest and cheapest to write down.

## What does NOT get stored

- Task state in semantic memory (goes stale silently; read NOW.md fresh).
- Anything the repo already records (code structure, git history).
- Visual verdicts — those belong to the user, only their *decision* is
  recorded.
- Rules without a named failure. If nothing paid for it, it is an opinion,
  and opinions go in the inbox to earn their way up, or nowhere.
