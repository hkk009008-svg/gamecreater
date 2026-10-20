# A visual production workflow for the Roblox team

This repo can give artists and agents a repeatable way to reach a distinctive,
coherent visual result: a clear target, reusable construction rules, controlled
comparisons, technical inspection and useful feedback. The game owner implements
and tests game content. This guide adds no Studio, asset, upload or spending
authority. "Frontier quality" is an ambition judged against chosen references
and actual play, not a status conferred by a test score.

## Start with a small visual target

Use the [visual brief](../templates/ROBLOX-VISUAL-BRIEF.template.md) inside the
existing task contract. For substantial visual direction or presentation changes,
name who owns the direction, the bounded implementation and independent critique;
these are responsibilities within the existing team, not three required new
agents. Ordinary local edits retain the existing focused-check workflow.

Define one visual promise, three recognizable rules and three reject examples.
Collect a small reference board with source links and the exact principle each
reference demonstrates: shape, material scale, light, composition or motion.
Record usage rights before turning reference assets into game content.
Concept images communicate intent; they do not prove that the renderer can
produce it or that the game already does.

Pick one ordinary gameplay view and one short combat sequence as the first
target. Include the real HUD, character, weapon and effects. Polish that slice
before propagating its vocabulary across maps. Do not let an attractive empty
hero shot stand in for the view players actually see.

## Improve the visible hierarchy first

| Priority | What to design | What a comparison should answer |
|---|---|---|
| First-person composition | Weapon and hands, aim corridor, HUD density, target silhouette | Can a player read the fight without the foreground competing with it, across the supported weapons and aspect ratios? |
| Large and medium shapes | One recognizable landmark, clear routes, intentional negative space, secondary detail | Does the arena have a memorable identity and readable depth at normal play distance? |
| Material construction | Edge thickness, joins, folds, grain scale and restrained wear appropriate to the art direction | Does the object read as its intended material in close, middle and far views, including motion? |
| Lighting | Key/fill relationship, contact grounding, controlled highlights and separation | Does light describe the forms while keeping characters and routes legible? |
| Motion and effects | Consistent timing, anticipation, impact, decay and recovery | Does a short gameplay sequence feel authored and readable without obscuring aim or changing game rules? |
| Cross-map consistency | Shared vocabulary with a distinct landmark/material motif per map | Do all supported maps, bot containers and player states receive the intended treatment? |

For a paper-diorama direction, plausible proposals include visibly layered card,
selective folded seams, cut-edge thickness, localized grain and printed markings,
with lighting that reveals their depth. Use these selectively at player-visible
scale. Dense outlines, uniform noise and more particles are not quality targets.
Preserve the game's accepted palette, collision, aim, silhouettes and timelines
unless the current user task explicitly changes them.

## Make comparisons trustworthy and inexpensive

Capture a baseline and at most two deliberate variants. State the one visual
question being tested; do not vary materials, exposure, camera and effects
simultaneously. Reuse working game capture/review helpers after inspecting their
current entry points and side effects; do not copy another whole QA framework.

Each comparison records the saved build/hash, map, ordinary entry, real subject,
camera/FOV, viewport, graphics setting, lighting, device/context, relevant random
state and elapsed point in the sequence. Record actual values, not just requested
ones. Derive camera anchors from the current scene instead of copying coordinates
from a different map. Cold saved-source identity is a separate preliminary check.

Show the same frame/time side by side, with an unmodified full frame and optional
labelled crops. Include motion for shimmer, clipping, animation and effect timing.
Use a short defect list: location/time, visible problem, likely responsible layer,
one proposed experiment and the condition for keeping or reverting it.

Before using a measurement, establish capture eligibility:

- Show a known-visible control from each relevant rendering/UI layer through the
  chosen capture path. A capture that omits BillboardGui cannot qualify ally pips.
- Confirm the subject is present, visible and at the intended distance. An
  occluder or empty selection invalidates that sample.
- Record original dimensions and encoding. Lossless unscaled captures are needed
  for fine grain, aliasing and small pixel-delta measurements; JPEG can still
  support labelled aesthetic review.
- Take an unchanged repeat pair and measure the baseline variability. Moving
  geometry, exposure and resampling cannot silently become an "effect delta."
- Keep spatial aliasing diagnostics, native motion, aesthetic judgement and
  gameplay readability as separate conclusions. A number cannot grade beauty.

The deliverable is a small comparison packet with a clear verdict and open cells,
not a growing checklist of every possible visual test.

## Choose quality within an actual device budget

The shared art direction should survive lower quality levels. Prioritize
silhouette, palette, focal hierarchy and key cues; reduce expensive decoration
before readability. Reuse meshes/materials and inspect transparency overdraw,
shadow cost and frame work before adding effects. Roblox documents these costs
and profiling paths in [Improve performance](https://create.roblox.com/docs/performance-optimization/improve).

Choose a real baseline device and set measured frame-time, memory and load-time
targets. A Studio aspect-ratio emulator does not establish physical-device
performance; see [Design for performance](https://create.roblox.com/docs/performance-optimization/design).
State median/tail behavior and test conditions when samples support them; one
fast frame or one effect's timing is not a total game performance result.

Select lighting for the art direction and test its quality scaling. Roblox's
current [Lighting documentation](https://create.roblox.com/docs/reference/engine/classes/Lighting)
distinguishes Soft and Realistic intent and explains that shadow behavior also
depends on quality settings. A settings label alone is not a visual verdict.
Sources checked 2026-10-20; recheck at implementation when a decision depends on them.

## Use the visual workbench

The existing task/review methods supply ownership and exact evidence identity.
The [visual workbench](roblox-visual-workbench.md) packages original captures,
paired motion, the art brief and missing coverage into one offline comparison
page. Its starter command hashes the supplied media; recorded settings and
capture-path controls determine whether a pair is eligible for a controlled
comparison. Unknowns remain visible. It assigns no automatic beauty score.
Use existing game helpers for capture, masks and measured repeat variability;
the workbench organizes their evidence without launching Studio.

After a successful slice, record a compact recipe: purpose, authoring parameters,
scale range, quality fallback, example evidence and known failure cases. Promote
only recipes that work in the saved build and relevant gameplay/device contexts.
The resulting small library is more useful than copying all game-specific code,
a long unverified art specification or an uncurated asset pack.

Local observation and existing helper pointers are recorded in
`team/visual-capability-audit-20261020.local.md`. That is a dated study, not
permission to replace the game's roadmap or evidence of current visual acceptance.
