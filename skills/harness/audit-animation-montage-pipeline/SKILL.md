---
name: audit-animation-montage-pipeline
description: Headlessly validate animation montage tracks, notify state windows (AnimNotifyState), combo branch timing, and root motion translation across skeletal meshes. Use when authoring or debugging combat notifies, trace windows, and animation blending.
---

# Audit Animation Montage Pipeline

Animation montages drive combat timings, collision trace windows, and motion warping. A misplaced or duration-zero AnimNotifyState causes attacks to deal zero damage or deal damage infinitely, while root motion mismatches cause pawns to snap back or float.

## When

1. Setting up or debugging combat hit windows (`DamageWindow`, `TrailEffect`, `ComboBranch`).
2. Retargeting animation montages to a new character skeleton.
3. Diagnosing root motion desync where animations play in place instead of moving the capsule.

## Invariants

1. **Notify Window Validity**: Every `AnimNotifyState` must have `NotifyBegin < NotifyEnd`. An end trigger at or before begin time never executes tick payloads.
2. **Slot Name Alignment**: Montage slot names (e.g. `DefaultGroup.UpperBody`, `FullBody`) must match the active AnimGraph slot node configuration; otherwise, montages play silently with zero pose override.
3. **Frame Rate Invariance**: Notify triggers must not be placed within a single-frame window (<16ms) that can be skipped during frame drops or sub-stepping ticks.
4. **Root Motion Translation**: If `EnableRootMotion` is true, the animation curve must contain translation on the root bone, and the character movement component mode must support root motion during montage playback.

## Verification Protocol

1. **Headless Python Reflection**:
   - Query montage length, slot groups, and sequence assets via Python API (`unreal.AnimMontage`).
   - Dump all AnimNotify / AnimNotifyState tracks and assert start/end timestamps.
2. **Tick Soak Probe**:
   - In a headless testbed, play the montage on a spawned actor and record notify event firings in the log.
   - Assert that `NotifyBegin` and `NotifyEnd` fire in strictly sequential order with valid payload references.

## Provenance

Combat notify timing defect (2026-08): Damage window notifies were set to frame 0 duration on AM_KG_DS_* montages, causing combat collision sweeps to never activate during fast attacks.

## Changelog

- 2026-08-14 — Authored for combat animation and notify pipeline verification.
