---
name: checkpoint-a-hold
description: What must be true before claiming a safe stopping point — NOW.md current, register tiered, lessons swept, work committed — so the next session starts oriented instead of blind. Use before ending an arc, declaring a hold, or any "commit push".
---

# Checkpoint a Hold

This skill grants no commit or push authority; it defines what a
checkpoint must contain, and the push remains a separately authorized act.

## When

You are about to stop — end of session, end of arc, user stepping away, or
a "commit push" request. The minutes before a hold are when context is
richest and cheapest to write down, and the recorded failure this ritual
prevents is precise: the next session re-deriving state from chat memory,
starting on a stale assumption, and paying full price to rediscover what
this session already knew.

## The ritual

1. **Update NOW.md** (the game's current-truth file):
   - current arc and where it stands, as of a named commit or run;
   - the **next executable action** — one concrete action with the file or
     command it starts from, not a theme;
   - the open register, tiered by what each item blocks (playing >
     quality > nothing), each entry with its evidence ref;
   - active blockers, including decisions waiting on the user;
   - the standing facts a fresh session gets wrong without this file —
     pruned, not accumulated.

2. **Sweep loose lessons** from the session into the inbox(es). Anything
   paid for and not yet written down dies with the scrollback.

3. **Reconcile the register.** Items closed this session move to the
   closed section WITH the evidence that closed them; a register that only
   grows stops being consulted. New known-untrusted instruments get named.

4. **Commit** the work and the updated state files together, with the
   repo's commit discipline. Quote `origin/main..main` count — a non-zero
   answer is that many commits on exactly one disk (see
   `pin-a-content-boundary`); the push itself stays the user's call.

5. **Say what kind of hold this is.** A safe hold means: no in-memory
   state is being mistaken for durable progress, everything cited is on
   disk, and the next action is executable by a session with no memory of
   this one. If something live is uncaptured — an unsaved candidate, an
   unverified fix — the hold is not safe; say so and either capture it or
   record it as the top blocker.

## The test

Read NOW.md cold, as the next session will: can you reconstruct the arc,
the next action, and the traps from that file alone (plus what it links)?
If anything essential lives only in this conversation, the checkpoint is
not done. This is the orientation drill; it is cheap, and it is the whole
point.

## Anti-patterns, each observed

- **The hold that skips the state write** because "it's all in the chat" —
  chat context is summarized, truncated, and eventually gone; the
  richest-context moment becomes the blindest spot.
- **Vague next actions** ("continue combat work") — the next session burns
  its first hour rediscovering what concrete thing was next.
- **The ever-growing register** — untiered, unclosed, unconsulted.
- **Claiming safe while a candidate is live and uncaptured** — report the
  live state as a blocker instead; a lock-screen or crash between now and
  next session loses it.

## Provenance

Distilled from the originating corpora's long-horizon checkpoint
discipline (objective, scope, evidence refs, next executable action —
"durable shared state beats chat memory") and from the measured cost of
its absence: sessions that started blind at exactly the point where the
previous one held the most context.

## Changelog

- 2026-08-12 — Initial authoring.
