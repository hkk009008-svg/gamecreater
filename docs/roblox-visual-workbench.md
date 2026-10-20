# Visual workbench

Use this tool to make a visual experiment easy to inspect: its intent, original
frames or sequences, comparison conditions, gaps and decision travel together.
Start with one ordinary gameplay view and a concrete question from the
[visual production workflow](roblox-visual-quality.md). The tool runs offline
and writes only new local harness artifacts. It does not capture Studio,
implement game art, publish, measure frame rate or judge beauty.

## Start a study

Python and Pillow are required. Existing capture helpers supply the images and
video. Choose original files, then run from the harness root:

```powershell
python scripts/roblox_visual_packet.py init --media D:/Game/evidence/before.png --media D:/Game/evidence/after.png --out team/material-study.local.json --title "Card edge depth"
```

`init` accepts repeated `--media` arguments, hashes the original bytes and creates
a fresh `.local.json` file inside the harness. With two or more captures it
prepares an aesthetic comparison using the first two; additional media becomes
reference material. A single capture creates a gallery. It leaves unmeasured
settings unknown instead of guessing them from filenames or image dimensions.

Edit the generated JSON:

- State the visual promise, rules, rejected outcomes and accepted choices to
  preserve. Ask one question and name the next experiment.
- Record actual build identity and capture settings from existing evidence.
  A file hash verifies identity; a declared build link still needs provenance.
- Identify the subject and relevant rendering-layer controls. Keep unknowns
  `null`, or `unknown` where the schema provides that enum.
- Add coverage rows for the maps, player views, UI states or devices relevant to
  this experiment. An empty `captureIds` list makes a missing view explicit.
- Keep the decision pending until a reviewer supplies a verdict. Record the
  user's actual judgement separately.

The [manifest template](../templates/ROBLOX-VISUAL-PACKET.template.json) documents
the shape. Its placeholder paths and hashes must be replaced before use;
`init` is the easier starting point.

## Check and build

```powershell
python scripts/roblox_visual_packet.py check --manifest team/material-study.local.json
python scripts/roblox_visual_packet.py build --manifest team/material-study.local.json --out team/visual-packets/material-study-001
```

Build output must be a new directory beneath `team/visual-packets/`. Existing
output is never overwritten. Each packet contains `index.html`, `manifest.json`,
`report.json` and a `media/` directory with byte-identical originals named by
hash. Keep the folder together. Open `index.html` in a browser; no server or
network service is required for the packet itself.

The page shows the brief, comparison selection, original full frames, settings
differences, evidence gaps, reference gallery, coverage and recorded decision.
Eligible image pairs of equal dimensions gain a movable overlay. Paired videos
can start approximately together; browser playback is not frame synchronization.
Videos remain available for critique even when their comparison is ineligible.

The page is a review artifact. Review controls do not save decisions or rewrite
the manifest. Edit the source manifest and build a new packet to record a new
verdict. Generated packets and `.local.json` manifests are ignored by Git; they
can contain game evidence and machine-local source paths.

Exit status distinguishes invalid input from evidence gaps:

| Result | Normal check/build | With `--require-comparable` |
|---|---|---|
| Valid inputs, eligible comparisons, requested coverage present | 0 | 0 |
| Valid inputs with unknown settings, missing coverage or ineligible pairs | 0, `needs-evidence` | 2 |
| Invalid manifest, changed media hash, unsafe path or unsupported file | Nonzero; no completed packet | Nonzero; no completed packet |

With `--require-comparable`, a structurally valid build still produces the useful
packet before returning 2 for evidence gaps. A gallery with no comparisons is
always `needs-evidence`. `ready-for-review` means the recorded comparison
conditions meet this tool's rules. It is not a visual acceptance verdict.

## What comparison eligibility means

Both sides need known build IDs/hashes, map, subject, phase, camera, FOV,
viewport, quality, lighting, device, random state, input and capture mode.
Settings must match except for at most one explicitly declared changed context
factor. A declared factor must still have known values. Build identities may
differ because a candidate usually changes the game.

For images, the recorded viewport must match the decoded image dimensions.
The subject must be explicitly visible. Each required rendering layer needs a
visible control and a retained capture reference; a capture can reference itself
when the visible control is explicitly identified. A control reference must use
the same capture mode, viewport and quality as its subject capture.

| Purpose | Additional requirements and limits |
|---|---|
| `aesthetic` | PNG or JPEG can support visual critique. Lossy originals remain labelled as such. No pixel score is calculated. |
| `pixel` | Both sides and their unchanged repeats must be lossless PNG, declared unscaled, with qualified subjects and controls. Each repeat needs the same build and context as its side and a distinct original media path. The tool checks prerequisites; it does not measure a noise floor or compute the visual delta. |
| `motion` | Both sides must be declared native video with native input and MP4 media. A stepped capture remains reviewable but cannot qualify as native motion. No performance or real-time playback claim follows. |

Eligibility is conditional on the supplied declarations. The workbench cannot
prove that the recorded camera was used, that a screenshot contains a control,
that the saved build was the running source, or that input came from a physical
device. Inspect the original capture-sidecar and runtime evidence when those
claims matter. A metadata comparison does not replace those observations.

## Manifest and file boundaries

Version 1 uses strict JSON: duplicate keys, unknown fields, non-finite numbers,
unknown references and invalid enums fail. Top-level fields are `schemaVersion`,
`title`, `question`, `direction`, `captures`, `comparisons`, `coverage` and
`decisions`. Capture containers `media`, `build`, `context`, `eligibility` and
`notes` are explicit; unavailable context values are normalized to unknowns.
The template enumerates the supported capture fields.

Local media may be absolute paths or paths relative to the manifest. Network
URLs and symlink/reparse paths are refused. PNG/JPEG images are decoded with
Pillow; MP4 files receive a format-signature check, not a codec or playback test.
Limits are 100 captures, 128 MiB per media file, 512 MiB combined media and
2 MiB for a manifest. The renderer only emits locally bundled media URLs,
escapes supplied text and includes no external assets, telemetry or scripts.

This tool deliberately packages evidence instead of introducing a new release
gate. Use the existing task, saved-build and review workflow for implementation
and handoff. A useful visual recipe should record parameters, scale range,
fallback, accepted examples and known failure cases once it has worked in the
saved game and relevant play/device contexts.
