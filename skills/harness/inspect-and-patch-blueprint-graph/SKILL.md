---
name: inspect-and-patch-blueprint-graph
description: Headlessly inspect Blueprint Class Default Objects (CDOs) and graph variables via reflection or harvest, generate valid ASCII clipboard node snippets for user assembly, and prevent destructive binary .uasset corruption. Use when modifying or diagnosing Blueprints without interactive editor corruption.
---

# Inspect and Patch Blueprint Graph

Binary `.uasset` files cannot be safely serialized or patched by text substitution. Modifying raw bytes or CDO properties without engine reflection leads to cyclic compilation deadlocks, pin disconnects, and fallback to parent defaults.

## When

1. Investigating a broken pin, variable default, or missing interface binding in a Blueprint class.
2. Generating a node network or function graph for the user to assemble in the editor.
3. Modifying class default properties (CDO) headlessly via embedded Python (`unreal.EditorAssetLibrary` or `unreal.load_asset`).

## The Four Traps

1. **In-Memory Compilation vs Cold Load**: A Blueprint modified in an active session can compile green while failing serialization on disk. Always verify by cold loading the asset in a fresh headless process.
2. **Enum Pin Re-indexing**: Changing an underlying C++ or UserDefinedEnum shifts integer indices without updating node pin values, causing silent runtime misbehavior. Recover original index layouts from asset string tables before altering enums.
3. **Circular Compilation Deadlocks**: Blueprint A referencing Blueprint B as a component type while B casts to A. Always verify dependency DAGs before introducing bidirectional references.
4. **Binary Substitution Corruption**: Never perform binary byte replaces on `.uasset` headers or graph sections. Use text clipboard serialization or Python API reflection.

## Clipboard Node Protocol

Unreal Engine Blueprint graphs can be copied and pasted as plain text ASCII blocks (`Begin Object Class=/Script/BlueprintGraph.K2Node_...`).

When providing nodes to the user:
1. Structure the node text with explicit `NodePosX` / `NodePosY` offsets so pasted nodes do not overlap.
2. Pin type definitions must match exact object paths (e.g. `/Script/Engine.Actor` or `/Game/.../BP_Character.BP_Character_C`).
3. Provide step-by-step assembly instructions: copy ASCII block -> focus Event Graph -> `Ctrl + V` -> connect execution pins -> Compile & Save.

## Evidence Rules

- Cite the property reflection name as dumped by the engine's embedded Python.
- Cite the cold-boot compile status from the engine log (`LogBlueprint: Display: ... compiled successfully`).
- Never claim a Blueprint fix is complete until verified on a fresh-spawn instance in a `-game` boot (`verify-on-the-real-entry`).

## Provenance

Learned from combat-wiring and impact-effect repair arcs (2026-08): in-session Blueprint compiles reported clean while saved disk bytes failed on cold load, causing player pawn fallback to default parent class.

## Changelog

- 2026-08-14 — Authored for headless Blueprint reflection and clipboard exchange workflows.
