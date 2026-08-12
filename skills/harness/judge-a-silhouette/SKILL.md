---
name: judge-a-silhouette
description: Turn a character render into a hole verdict no later edit can talk its way out of. Covers the black-on-black hole a pixel diff scores at zero, the thousands of enclosures a dressed world produces on its own, the subject-hidden plate that cancels them, and the mirror defect this check is blind to. Use before accepting a render, calling a hole closed, or saying cloth covers skin.
---

# Judge a Silhouette

This skill grants no engine-launch, content-write, or accept-list-edit
authority. A subject-hidden plate costs 2x render time per QA frame — a
separately authorized launch, not a free flag.

## When

You are about to accept a character render, or call yesterday's hole
closed. Eyes are the wrong instrument for the first claim and a pixel diff
is wrong for both: background through black cloth on a black backdrop is a
delta of ~0, and a raw pixel-count metric scores a compact hole and the
same number of scattered anti-aliasing pixels identically. A hole is a
**topology** fact, not a colour fact, so the instrument asks the one
question no edit can argue with: is background-coloured area enclosed
inside the subject without touching the frame border?

The originating failure: every check that existed passed while a window
stood open in a character's shoulder for a day, because each check was
authored beside the edit it validated. A check that knows only the edit
that motivated it cannot catch the class of defect it was never pointed at.

## Enclosed background that does not touch the border is a hole, exactly

Background touches the frame border by definition, so background-coloured
area with no border flag is background seen *through* the subject. That
invariant is exact rather than learned — which beats any trained artifact
detector whose unseen-content accuracy is a coin toss. Implementation:
4-connected labelling by row runs + union-find, one pass, no heavy
dependencies (installing scipy into an embedded engine interpreter is a
fight you lose). Where a real alpha channel exists the test becomes exact
and immune to black-on-black: any near-zero-alpha component with no border
flag is a hole.

## An absolute region count is not a gate — a dressed world encloses background

Measured: absolute mode over 7 dressed scene plates reported 2,180 regions
— stepping stones, hedge gaps, and archway openings all legitimately
enclose background — with the 2 real defects hidden in the pile. Three
escapes, in increasing order of principle:

| Mode | Requires | What cancels |
|---|---|---|
| accept-list | human-recorded JSON of legitimate enclosures | nothing; you are annotating noise |
| baseline diff | two runs, same cameras and world, differing only by the edit | every world-caused region pairs off |
| subject-hidden plate | a plate render of the same cameras | the world cancels by construction |

Baseline mode pairs regions by bounding-box overlap and emits closed /
shared / new, of which only **new** fails — answering the question a fix
needs answered: *did the window close without opening another?* That makes
it the primary mode. Plate mode took the same 7 frames from 2,180 regions
to 55.

## Cancellation is valid only if everything except the subject is identical

One eye-adaptation shift or one resident mip difference poisons the whole
frame, so plate and beauty share warm-up count, frame index, cvar state,
ideally one process. **Matte differencing is MORE sensitive to
nondeterminism than perceptual diffing** — warm-up is a prerequisite, never
a follow-up. Temporal AA history converges over ~8-16 frames and
screen-size LOD selection changes the silhouette outright; pin both. Two
more preconditions, both measured: hiding the subject changes the world
(contact shadows, GI, reflections — disable dynamic GI and subject shadows
for the QA plate), and **assert the beauty render differs from the plate**
— if the subject failed to spawn, every pixel reads as background and the
check exits clean.

## Plate mode is a strong absolute detector, not a complete one

One real window was found by baseline diff and NOT flagged by plate mode,
because hair strands crossing the opening shifted its colour past the
tolerance. Keep both modes in service. And when a window survives, bisect
by lever, not by argument: five renders, one lever each, same region box —
three suspects innocent to the pixel, hiding hair made the window *bigger*
(hair was capping it), and disabling one morph closed 82% of it. The cause
was a displacement baked into one mesh's base LOD pulling a shared seam
apart: **an edit validated against what it was FOR and never against what
it BOUNDED.** Measure a mesh-to-mesh edit at the join it shares, not only
in the middle.

## Black-on-black is the blind spot; the fix is a backdrop, not a lower tolerance

A real hole measured near-identical RGB to the sky behind it, bounded by
black cloth — visible in 6 of 7 scene frames and 0 studio plates, because
a hole over a black background is black on black at every threshold.
**Separate a hole from a texture with two plates on two different
backdrops** — a saturated chroma-hostile colour serves. The cheap second
corroborator is a scene-depth capture: shading-independent, immune to
black-on-black entirely. Agreement between colour matte and depth matte is
strong evidence; disagreement localises the bug.

## The instrument is structurally blind to the mirror defect

Enclosed-background finds background *inside* the silhouette. Poke-through
is skin *outside* cloth — the mirror defect — invisible to this tool at any
tolerance. Two routes for the missing instrument: geometric (min clearance
per covered vertex — zero renders, names the bone; but bind-pose only), or
pixel (force the skin material to a key colour and count pixels per pose).
Poke-through is a per-frame, per-vertex event: it can occur for 3 frames of
a 120-frame sweep and be invisible in every still. **An instrument's blind
spot is a property of its invariant, and it does not shrink when you tune
the instrument.** Write the blind spot beside the instrument, or the next
reader cites a clean plate run as coverage.

## An accept-list that grows every time the check fires is a check switched off

An accept-list entry is a human judgement recorded in JSON, never a
measurement. Track the list's length as a metric with an alarm on its
growth rate: two entries covering a pierced ornament is a record; twelve
entries over four sessions is a disabled gate still reporting PASS.

## Identify every surviving region by name, or the count is a guess

A clean run is one where you can name what each remaining region *is* —
"three are the staff's pierced ring, one is the arm/torso gap showing
rim-lit contour." And a percentage closed is not a verdict: a fix that
took a window from 1,659 px to slivers of ~285 px was 94% closed and still
open. A region either exists or it does not. Close a reported hole on a
**re-report of the same frames**, never on a fix — one user-visible symptom
can have N causes, and fixing one looks exactly like fixing all of them.
File a second window as a second defect even when the symptom matches: one
defect ID can carry only one status.

## Prove the gate can fail before you cite a clean run

A closing criterion the roadmap waited on **had never been run** — a gate
that exists and never executes is indistinguishable from zero gates while
reading in a status report as one. Require the gate to report the
hand-verified fixture holes with their exact boxes before accepting its
silence anywhere else; then punch one quad out of a test mesh and require a
`new` region. Assert the degenerate cases too, because each produces
well-formed output and exit 0: beauty equal to plate (subject never
spawned), a uniform frame (camera inside geometry), a comparison against a
~130-byte LFS pointer instead of an image.

## Evidence rules

State the mode and every threshold alongside every region count — 2,180
and 55 were the same 7 frames, so a count without its mode is unreadable.
Cite the JSON the check wrote, never the check's existence. Record per
judged run: mode, plate/baseline directory, thresholds, shared capture
parameters, accept-list length, and per region its bbox, area, and
closed/shared/new class. If plate mode returns clean, say "clean under
plate mode" and name the two things it cannot see: the colour-matched
opening and the mirror defect.

Related: `establish-a-noise-floor` for whether a delta is an effect at
all; `prove-an-instrument-can-fail` for the positive control this demands.

## Provenance

The day-long shoulder window, the 2,180-region absolute count, the
five-lever bisection, and the black-on-black blind spot are measured
instances from one character-project corpus (2026-08). Generalized
2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
