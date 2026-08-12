---
name: watch-the-live-session
description: When the user reports a failure you cannot reproduce, look at their actual screen before theorizing — the decisive evidence is usually visible there and nowhere in your logs. Covers when to reach for a screenshot, what to look for first, and the capability asymmetry (screenshots work where remote input does not). Use on any works-for-me report, and before the second theory about the user's environment.
---

# Watch the Live Session

This skill grants no input-injection authority on the user's machine;
screen capture and any control require the user's explicit permission per
application.

## When

The user says "not fixed", "still broken", "same thing" — and your gate
passes. You are one theory deep and about to go two. Stop: the user is
looking at evidence you have never seen, and one screenshot of their
actual session is usually cheaper and more decisive than any hypothesis
you can test on your side.

Measured, twice in one arc:

- A "the character is broken again" report that survived two rounds of
  instance-level fixes was resolved by a screenshot showing a **compile-
  error banner** in the user's editor — in their UI language, in a corner
  of the screen, mentioned in no log either side had read. The error
  cascade it named was the entire bug.
- A "we control the wrong body" report was confirmed and localized by
  watching the user's play session: the pawn on their screen was the
  vendor's fallback body, which no headless gate on the author's side
  rendered at all.

Both were works-here-fails-there cases where the difference list
(`isolate-a-variable`) was long — and the screenshot collapsed it to one
column in seconds.

## What to look for first

1. **Error surfaces you don't have**: banners, toasts, message-log panes,
   red compile badges. Editors surface errors in the UI that never reach
   the logs a headless run writes.
2. **Which thing they are actually looking at**: the map open in their
   editor, the mode of their play button, the actor actually selected.
   Users and gates frequently run different entries
   (`verify-on-the-real-entry`).
3. **The state your fix should have changed**, as rendered on their
   machine — not as reported by your instrumentation.
4. **Language and locale**: the user's UI may be localized; match error
   strings by shape and position, and quote them back verbatim for the
   record.

## The capability asymmetry

Remote *observation* and remote *control* fail independently. Measured on
one setup: screenshots worked perfectly while remote clicks landed
nowhere (a DPI/coordinate mismatch) — so the working division of labour
was **I watch, they drive**: the user clicks, you direct from the
screenshot, step by step. Establish which half works once, early, and
design the collaboration around it rather than fighting the broken half.
When only observation works, precise instructions beat approximate
automation every time — the user is a better mouse than a misaligned
coordinate transform.

## Discipline

- Ask permission before capturing; say what you want to look at and why.
- Screenshot at the moment of failure, not after a cleanup — state decays.
- Capture the whole screen first, then zoom into regions; the decisive
  banner in the measured case was outside the area under discussion.
- Quote what you see back to the user in words before acting on it — a
  misread screenshot compounds exactly like a misread log.
- The screenshot is evidence: reference what it showed in the arc record
  (and attach the frame whenever a claim rests on how something looks —
  visual verdicts belong to the user).

## Provenance

Two decisive screen-watches in one combat-wiring arc (2026-08-11/12),
each ending a multi-round works-here-fails-there stalemate that log
analysis had not cracked; plus the measured screenshots-work/clicks-don't
asymmetry that shaped the watch-and-direct workflow.

## Changelog

- 2026-08-12 — Authored from the combat-wiring arc's inbox entries.
