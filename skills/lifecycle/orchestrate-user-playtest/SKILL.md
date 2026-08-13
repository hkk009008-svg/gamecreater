---
name: orchestrate-user-playtest
description: Brief the user with a structured, unambiguous test protocol when transitioning a feature from Rung 4 (headless -game verification) to Rung 5 (human playtest). Covers exact setup, step sequences, visual cue checklists, and structured feedback collection.
---

# Orchestrate User Playtest

Headless verification (Rung 4) proves that the map boots, classes instantiate, and logs stay clean. Only the human user (Rung 5) can close gameplay feel, animation fluidity, input response, and visual quality. A vague ask ("Please test it") wastes user time and generates unfalsifiable feedback.

## When

All automated rungs (in-session, cold reload, fresh spawn, `-game` headless boot) pass with zero compile or runtime errors, and the feature is ready for human validation.

## The Playtest Protocol Structure

Always format the playtest briefing with four distinct, concise sections:

### 1. Build & Map Setup
- Exact entry executable/mode: (e.g. *PIE Selected Viewport*, *Standalone Game*, or *Packaged Build*).
- Exact map name to open (e.g. `L_Playtest_Arena`).
- Starting conditions (e.g. "Equip katana from spawn pedestal 2m ahead").

### 2. Action Sequence (Max 3 Steps)
1. **Step 1**: Specific input action (e.g. "Press LMB 3 times to execute light attack combo").
2. **Step 2**: Positional interaction (e.g. "Walk into collision radius of target dummy").
3. **Step 3**: State transition (e.g. "Press H to sheath weapon during recovery window").

### 3. Observable Signals Checklist
- **Expected Visuals**: (e.g. "Red hit spark VFX spawns on contact; dummy flashes white").
- **Expected Audio / Telemetry**: (e.g. "Slash SFX fires on frame 14; damage number floating text appears").
- **Known Traps / Exclusions**: (e.g. "Hitbox trails are debug green for this pass; ignore trail color").

### 4. Structured Feedback Schema
Ask for discrete answers:
- **Verdict**: PASS / FAIL / BLOCKED
- **Symptom (if failed)**: What was observed instead of the expected signal?
- **Artifact**: Screenshot / short video clip if visual anomaly observed.

## Discipline

- Never ask more than 2 distinct gameplay questions per playtest round.
- Monitor log files live during the playtest session to capture unexpected Blueprint warnings or assertion failures.
- Record the user's verdict verbatim in `NOW.md` under the active arc register.

## Provenance

Combat-wiring arc playtest iterations (2026-08): vague playtest questions led to 3 wasted cycles where user was testing an unlinked test map rather than the canonical entry level.

## Changelog

- 2026-08-14 — Authored to standardize Rung-5 human verification handoffs.
