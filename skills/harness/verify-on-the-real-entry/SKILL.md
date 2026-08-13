---
name: verify-on-the-real-entry
description: A gate proves nothing unless it runs the consumer's actual path — fresh spawn instead of a patched instance, cold load from saved bytes instead of in-session state, the entry the product really boots instead of the map you opened by hand. Use before claiming any gameplay or integration fix is done, and whenever your gate passes while the user's session fails.
---

# Verify on the Real Entry

This skill grants no launch or write authority; it decides what a passing
gate is allowed to claim.

## When

You are about to claim a fix is verified, and your verification ran in an
environment you assembled — an editor session, a hand-opened map, a live
process with the day's work in memory. The player does not enter there. A
week of this class in one project produced repeated "fixed" claims the
user falsified on sight, because gate and player entered through different
doors. The user's standing correction, verbatim: *"remember that is not
the same starting point as real game play."*

## The five axes on which a test entry silently diverges

Enumerate all five every time; each one independently produced a false
PASS:

1. **Map.** A gate that opens the map explicitly proves nothing about what
   the product boots into. Measured: the project's game-default map still
   pointed at a retired lab scene, so every real launch skipped the
   playtest map — and everything wired into it — entirely. Read the boot
   config; verify on the map it names, or fix it first.

2. **Object identity.** Fixes applied to a placed instance are invisible to
   every fresh spawn of its class. The player's pawn is spawned fresh by
   the game mode; a patched level actor is a different object. Fix class
   templates; verify on a fresh spawn.

3. **State temperature.** In-session state masks load-time failures: a
   Blueprint that compiles clean in the live editor can fail compile on
   every cold load from saved bytes — and one vendor asset failing that way
   cascaded through an equipment manager into the player pawn silently
   falling back to its parent's naked defaults. "Compiles now" and "loads
   clean" are different claims; only a fresh process tests the second.

4. **Spawn point and flow.** A parked camera, a play-from-here, and the
   real player start produce different spawn locations and init ordering.
   Measured: an overlap-triggered pickup no-oped when the player spawned
   inside it, because the overlap fired before inventory init — the walk-on
   worked, the spawn-on never could.

5. **Disabled layers.** The consumer's entry includes every layer the gate
   turned off to run. Measured twice on 2026-08-13: a `-game -nullrhi`
   boot gate passed for days while five identical GPU faults lived in the
   ray-tracing path it never started; and a 47-green suite drove `main()`
   in-process against a StringIO — which never encodes — and the real
   console's cp949 codepage crashed the actual entry. Name what the gate
   disabled in every claim, and give any layer the failure could live in
   its own gate: a rendered soak with the RHI positively asserted, a
   subprocess entry test under the machine codepage.

## The gate ladder — each rung is a strictly realer entry

1. **In-session check** — cheapest, weakest; refactor feedback only.
2. **Cold reload** — bounce to a neutral map or restart the process, load
   from saved bytes, then check. Catches axis 3.
3. **Fresh-spawn check** — a new instance of the class through the real
   spawn path. Catches axis 2.
4. **Real boot** — launch the product the way the player does (for a game:
   `-game` mode, no editor, no hand-loaded map; headless with null
   rendering if only log evidence is needed — and say so: null rendering
   proves the CPU/content layer only, axis 5 stays open). The log must
   show the right map loading by itself, the right game mode class, the
   world up for play, and zero load-time errors. Catches axes 1 and 3 at
   once.
5. **The user plays it.** The only rung that closes a user-reported
   defect. Close on a re-report, never on a fix.

Claim at the rung you ran, explicitly: "verified at cold-reload" is honest;
"verified" after rung 1 is the recorded failure mode.

## Works-here-fails-there between you and the user IS this skill

When your gate passes and the user's session fails, the difference list
(per `isolate-a-variable`) starts with these four axes — and the fastest
discriminating read is usually looking at their actual session
(`watch-the-live-session`) rather than re-running yours.

## Evidence rules

Name the entry path in every verification claim: process (fresh/warm), map
(booted/hand-loaded), object (fresh spawn/patched instance), spawn point.
A claim that omits the entry path is unreadable — the same words "it
works" were true at rung 1 and false at rung 4 in the same hour. Record
the boot log lines that prove rung 4: map load, game-mode class, world up,
error count.

## Provenance

One week of a combat-wiring arc (2026-08-11/12): instance fixes invisible
to game-mode spawns, an in-session compile masking a cold-load cascade
that replaced the player's body, a game-default map pointing at the wrong
scene, and a spawn-overlap init race — four distinct false-PASS mechanisms
on one feature, each caught by the user, not the gate.

## Changelog

- 2026-08-12 — Authored from the combat-wiring arc's inbox entries.
- 2026-08-13 — Fifth axis (disabled layers) and the rung-4 null-rendering
  caveat. Forced by: five ray-tracing faults behind a green -nullrhi
  gate, and the scrub suite's cp949 real-entry crash (inbox entries of
  2026-08-13, both repos).
