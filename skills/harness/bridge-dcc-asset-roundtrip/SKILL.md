---
name: bridge-dcc-asset-roundtrip
description: Enforce coordinate conventions, bone hierarchy roots, scale units, and normal map tangents between DCC tools (Blender, Maya) and Unreal Engine. Use before exporting, importing, or re-rigging skeletal and static meshes.
---

# Bridge DCC Asset Roundtrip

Exporting and re-importing assets across DCC tools (Blender, Maya) and Unreal Engine creates subtle pipeline rot: coordinate flips, inverted normal map green channels, bone hierarchy duplication, and scale factor distortion.

## When

1. Exporting skeletal meshes or animations from Blender/Maya to FBX/glTF for Unreal.
2. Re-importing existing character garments, weapons, or groom bindings after DCC geometry edits.
3. Diagnosing coordinate system inversions (Z-up vs Y-up, left-handed vs right-handed).

## Core Traps & Rules

1. **The Blender Armature Root Trap**:
   - In Blender, the top-level armature object can become an extra root bone (`Armature`) in Unreal, corrupting animation retargeting and socket hierarchies.
   - *Rule*: Configure the FBX exporter to ignore armature root or name the root bone identically to the Unreal skeleton root (`root`).
2. **Scale Factor & Physics Capsule Distortion**:
   - Unreal uses centimeters (1 unit = 1 cm). Blender default is meters (1 unit = 1 m).
   - Exporting with mismatched scale units scales bone transforms 0.01x or 100x, corrupting physics asset capsule radii and root motion velocities.
   - *Rule*: Set Blender scene unit scale to `0.01` (Metric, Centimeters) before rigging or exporting.
3. **Normal Map Green Channel Tangent Space**:
   - Unreal Engine expects DirectX normal maps (Y- / Green channel pointing Down).
   - Blender and OpenGL use Y+ (Green channel pointing Up).
   - *Rule*: Invert the green channel on import or check the `Flip Green Channel` texture setting in Unreal.
4. **Vertex Color & UV Channel Mapping**:
   - Secondary UV sets (lightmaps, groom guides) and vertex color channels frequently re-index or drop during multi-step DCC roundtrips.
   - *Rule*: Assert UV channel count and vertex color presence before replacing existing game content.

## Headless Batch Scripting

Run DCC modifications headlessly using background CLI options:
```bash
# Headless Blender Python execution:
blender -b -noaudio asset.blend -P export_fbx.py -- output.fbx
```

## Provenance

Kurogane asset pipeline calibrations (2026-08): Character groom bindings detached and katana bone hierarchies broke due to extra Blender armature root bones during mesh re-import.

## Changelog

- 2026-08-14 — Authored for DCC-to-engine asset roundtrip integrity.
