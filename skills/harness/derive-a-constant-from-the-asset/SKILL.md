---
name: derive-a-constant-from-the-asset
description: Derive every landmark, camera aim, band edge, threshold and scale factor from the asset itself, so it moves when the asset moves. Covers the constant fitted to one subject that later fails as a plausible content bug, the cached dump gone stale, the band edge that lands on the wrong joint, and the derivation that is confidently wrong. Use before typing a geometry number into a script.
---

# Derive a Constant From the Asset

This skill grants no asset-write, capture-launch, or external-effect
authority.

## When

You are about to type a geometry number into a script — a camera aim, a
z band, a coverage threshold, a scale of "about 0.9". You measured it once,
it is correct against the asset in front of you today, and it will sit in
that file for months. Read it out of the asset at run time instead, because
a stale literal does not crash: **it returns a confident wrong answer that
looks exactly like a content defect**, and the next day goes to rebuilding
content that was never broken. Sixteen instances in the originating corpus
were correct on the day they were written, every one later went wrong
without raising anything, and three of them bought work on content that was
never damaged.

## A literal fitted to one subject fails as a content bug, not as a crash

A capture harness carried a head-camera aim fitted to one body height. The
character grew 13 cm; the head plates came back showing thin, sparse hair
where a full groom had rendered — the exact picture of a groom binding
failure, a class the pipeline had genuinely hit — and **the recorded next
action was a groom rebuild**. Re-aiming the cameras and changing nothing
else restored the full groom. Every machine-readable signal said the groom
was fine, because it was: the constant sits upstream of everything the
sentinel reads. **Distinguish a de-aimed instrument from damaged content by
re-aiming and changing nothing else** — one capture settles it; inspecting
the content settles nothing.

## Derive the band, then check it reproduces the literal exactly

A seam checker hardcoded the z band one body happened to have. The
replacement derives it from the two meshes it measures between
(`max(min_a, min_b) .. min(max_a, max_b)`) — and on the known-good state it
reproduced the old literal to three decimals, proving both halves at once:
the derivation is right, and the literal was never a property of the seam.
Run the derivation against the known-good state **before** deleting the
literal; a derivation that disagrees with a trusted constant is either a
better instrument or a broken one, and only the known-good state separates
those. And **commit the deriver**: the instrument behind one such
derivation was never committed and no longer exists anywhere — the numbers
survive, the ability to re-derive them does not.

## A landmark carried from memory is a plausible answer measured off the wrong region

A trimmer classified anatomy from centres transcribed from memory, 4 cm off
the fitted table's value; the region it labelled was not the region named,
and the script returned the *correct verdict by accident*. It was deleted,
not fixed: a destructive script that silently no-ops on a wrong constant is
the same failure class as a backup that never reached disk. A verdict that
happens to be right is not evidence the instrument works.

## Scale to a measured target dimension; one factor across a pack is a bug

Vendor meshes in one pack spanned a 4x authored-size range; a single
"about 0.9" scale placed background dressing taller than the hero. Scale
each placement to a measured target dimension; the resulting *spread* of
scale factors is the fix, because the meshes differ and the heights no
longer do. Siblings in the same commit: modular walls placed by count
instead of measured span (holes at both ends), ground cover placed at
authored size (chest-high thicket), stepping stones on a pitch nobody could
step. **A scale factor is a claim about a size you did not measure; a
target dimension is a claim about the size you want.**

## Read the pivot before placing; a pivot can sit metres from its own geometry

One roof mesh's pivot sat 6.8 m below its geometry — placing by pivot at
wall height hung it in the sky; a centred-pivot column stood through the
roof it supported. Probe `pivot_above_base` for every candidate mesh once,
and placement becomes a lookup instead of render-and-guess. Compute
min/max from bounds origin ± extent in one module that owns the
convention.

## A cached dump is a constant with a timestamp, so hash its source

A mask painter read a cached per-triangle UV dump that predated the
garment's geometry change by a day — it parses, the values are real, and
they belong to a mesh that no longer exists. Write the source asset's
content hash into the dump's header and refuse the read when it moves. A
premise about another asset's geometry is a **dependency**, not a comment.
The worst instance was two edits, each safe on its own recorded premise,
whose premises cancelled — geometry deleted under cloth that a later edit
moved, leaving a hole visible only against bright backgrounds. Two local
checks passed; what was missing was one invariant spanning both edits.

## Derive it twice with a refusal band, or the derivation is a new guess

Deriving moves the error out of the constant and into the heuristic. A
farthest-from-centroid landmark returned an anatomically impossible answer
and mirrored every downstream number. The fix: two independent
derivations **required to agree**, plus an outright refusal band. On limb
carves, a band floor must clear the **joint**, never the mesh minimum —
one carve bottomed out on the hand because the geometry did, and the user
saw "four hands."

## An assumed denominator does not add noise; it changes the sign

A proportion check normalised by an assumed 12 cm face height instead of a
measured one and returned 1.22 vs 0.99 — a sculpt pass was proposed on it.
Re-measured with both terms from the same instrument: 1.04 vs 0.99, inside
the uncertainty; the pass was withdrawn. The borrowed denominator did not
blur the answer, it inverted it. Check what a normaliser was measured for
before dividing by it.

## A landmark defined as a fraction moves whenever the pose moves

A silhouette comparator manufactured a 38-point failure entirely from
pose-tracking landmarks (a skirt band that caught the hands, a shoulder
scaled by outstretched arms, a "neck" found inside the hair). Define
landmarks in terms the pose cannot change, derive them from each other in
dependency order, and let the comparator report `n/a` on views the image
cannot support rather than a plausible wrong number.

## These symptoms all read as damaged content and all are a stale number

| What you see | What it is |
|---|---|
| Hair/detail reads sparse; every readiness signal healthy in both runs | a camera-aim literal fitted to the old subject |
| A metric drifts across a sweep with no edit between variants | a hardcoded band naming a different region per variant |
| A verdict correct while the count it acted on is implausible | a landmark transcribed from memory |
| A mask repaints and nothing moves, or moves wrongly | a cached dump older than the last geometry edit |
| Background dressing out-scales the hero; modular runs leave gaps | one scale factor across a 4x authored-size spread |
| A prop hangs in the sky or stands through its support | placement by unmeasured pivot |
| A carve keeps geometry it was written to exclude | a band edge from the mesh minimum instead of the joint |
| A proportion wrong by a margin nothing corroborates | a ratio normalised by an assumed denominator |
| A comparator fails repeatedly while the build did not move | landmarks defined as fractions of pose-dependent extents |

## Constants live in one imported table

One machine-readable table of landmarks, band edges, camera aims, and
thresholds, derived from measurement, imported by everything. A constant
with three homes (a doc, a script, somebody's memory) has no home — the
originating corpus's three copies of one landmark disagreed by 4 cm. When
a constant genuinely cannot be derived yet (an instrument is hash-frozen),
register the literal as an open defect rather than letting it pass as
solved.

## Evidence rules

State the asset and the run a constant came from, beside the constant. A
number without its source is unfalsifiable prose; `[a, b] derived from
<asset> at <hash>` can be re-derived and can disagree with you. When a
render looks wrong, **re-derive the constants that aimed the instrument
before touching the content** — one launch, against an alternative that has
already bought a needless rebuild, a deleted probe, and a withdrawn sculpt
pass.

Related: `prove-an-instrument-can-fail` for making the derivation fail on
purpose; `write-a-run-sidecar` for stamping derived values and source
hashes into the artifact that used them.

## Provenance

Sixteen stale-literal instances from one character-project corpus
(2026-07/08), three of which bought work on undamaged content. Generalized
2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
