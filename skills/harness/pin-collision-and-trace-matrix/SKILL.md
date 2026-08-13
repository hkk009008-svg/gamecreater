---
name: pin-collision-and-trace-matrix
description: Validate collision channels, trace query responses, and physical interaction profiles defined in DefaultEngine.ini and Blueprint components. Use when debugging weapons falling through the world, trace queries missing targets, or unintended pawn overlaps.
---

# Pin Collision and Trace Matrix

Collision channels and response presets define what hits what in gameplay. A subtle typo in `DefaultEngine.ini` or an unpinned collision preset on a mesh component causes weapons to fall through terrain, attacks to hit invisible walls, or projectiles to pass through enemies.

## When

1. Adding custom collision object channels or trace channels (e.g. `ECC_GameTraceChannel1` -> `WeaponTrace`).
2. Setting up combat weapon hitboxes, projectile collision bounds, or camera collision probes.
3. Diagnosing objects falling through world floors or passing through enemies without overlap events.

## Invariants

1. **Bidirectional Symmetry in Overlaps**: For an `Overlap` event to fire between Actor A and Actor B, **both** Actor A must set ObjectType B to `Overlap` (or `Block`), and Actor B must set ObjectType A to `Overlap` (or `Block`), and both must enable `GenerateOverlapEvents`.
2. **Channel Mapping Invariance**: Engine config maps custom channels (`ECC_GameTraceChannelX`) to display names in `DefaultEngine.ini`. Array lines written without `+` overwrite previous channel definitions.
3. **Complex vs Simple Collision**: Line traces querying `TraceComplex=false` will fail if static meshes lack simple collision geometry (convex hulls, boxes, or capsules).

## Verification Method

1. **Config Diff**:
   - Inspect `Config/DefaultEngine.ini` under `[/Script/Engine.CollisionProfile]` and assert all custom channel declarations and profile responses.
2. **Headless Sweep Probe**:
   - Spawn the actor in a test level and execute a headless line trace / sphere sweep across the target actor.
   - Assert `bBlockingHit`, `HitResult.GetActor()`, and `HitResult.GetComponent()` match expectations.

## Provenance

Equipment spawn pad calibration (2026-08): Katana weapon pickups fell through terrain geometry because custom weapon channel was set to `Ignore` on WorldStatic collision preset.

## Changelog

- 2026-08-14 — Authored for collision profile and trace matrix verification.
