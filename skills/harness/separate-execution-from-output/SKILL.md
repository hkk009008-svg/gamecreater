---
name: separate-execution-from-output
description: Make a run emit two verdicts — did the script run, is the artifact correct — so a green sentinel stops standing in for a rendered image. Covers PASS over black frames, an empty error list on a broken character, totals that clear while one part is missing, silent N-step binding chains, and a check that can never pass. Use before reporting a run as PASS or gating anything on a sentinel.
---

# Separate Execution From Output

This skill grants no render-accept, canonical-write, or external-effect
authority; it decides only what a completed run is allowed to claim.

## When

You are about to report a run as PASS, or read an empty error list out of a
run report and treat the artifact as good. The script completing and the
artifact being correct are two different claims, and a sentinel the script
wrote can only ever answer the first.

## An execution verdict cannot see whether the lights were on

Measured instances — one project, one sentinel string, five failures, every
one with the sentinel green and the error list empty:

| What the sentinel said | What the pixels said |
|---|---|
| PASS on 7 capture frames | mean luminance ~1 — the map had no light at all |
| PASS, valid component bounds, groom waits healthy | a bald character: 180k hair curves rendering nothing |
| PASS for days, across four grade rounds and three wrong theories | five garments rendering the engine fallback checker, which read convincingly as dark banded fabric |
| PASS with both paint-coverage aggregates clearing their floors | a per-digit mask with one digit bare |
| PASS, twice, on two full renders | 0 pixels changed, twice |

All five were caught by looking at the pixels; zero by the sentinel. The
black-frame row had a cause no execution check could reach: the sky was a
Blueprint that positions its sun **on tick**, and the headless one-shot
never ticked it — the script ran perfectly and lit nothing.

## Ship two verdicts, and only the second may accept an artifact

**EXECUTION** answers *did the script run*: exit status, exception count,
steps completed. **OUTPUT** answers *is the artifact correct*, and it is a
committed instrument that prints a number you can cite later. A run is
accepted only when OUTPUT clears, and OUTPUT must be able to fail on a run
whose EXECUTION is clean — that is the entire reason for separating them.

The minimum OUTPUT set, each traceable to a row above: minimum lit
luminance, minimum light-actor count, the expected component set, and
per-part coverage. Assert all of them in-script, in the same process that
produced the artifact, so there is no second launch to forget.

## Assert per-part, never per-total

**A total is admissible only alongside an assertion on the partition.** The
per-digit mask cleared both aggregate floors while one digit carried
nothing — found only by decoding the mask and back-mapping each blob. The
replacement declares its partition and asserts on it: every digit owns at
least one lit texel, seeds at least a minimum distance apart, fill ratio
above a floor — verified offline before the import. More totals that
acquitted where the partition convicted: whole-asset renders that looked
like fabric vs a per-triangle material-ID histogram; a whole-plate delta
below the noise floor vs the same change measuring 7x inside the object's
own region against a 0.00% control there.

## Gate on a census, not on a sentinel

**Count the things that must be present, and fail on the count.** The
rebuilt scene refuses to render with fewer than its named minimum of
lighting actors, and spawns them explicitly rather than assuming them. A
census enumerates the world the renderer is looking at; a sentinel
enumerates the steps the script believes it took. Apply the same shape to
components: assert the expected set is present, not that zero errors were
raised while assembling it.

## Every link of an N-step chain resolves non-null, or you render the old state

Adding one texture was four steps: author it, import it, register the
alias, point the material slot at it. Doing steps 1 and 4 alone changed the
render by exactly zero pixels, twice — the alias resolved to `None`, the
material received nothing, and the garment silently kept its donor's look.
A second route into the identical symptom: a dispatch table keyed on
component labels silently skips any component whose label is absent. Emit a
resolved manifest as an artifact and assert every link non-null; give every
string-keyed dispatch table a completeness assertion against the live
component list — a comment saying "keep in sync" has already failed.

## A check that cannot pass is worse than no check

**It trains you to ignore the sentinel.** One predicate ignored a
containment fringe and therefore could not pass on any correct cut, so its
failure carried no information and was read as noise. Its sibling compared
against a reference that included the arms — the wrong reference for a
sleeveless design — and flagged a band the cut never touched.
**Distinguish a working OUTPUT check from a decorative one by running it
twice — once on the known-good state and once on the known-bad state** —
not by whether it went green on the artifact it was written for. A check
that has only ever returned one answer has demonstrated nothing about the
other.

## A tell that is documented but not computed is not a control

One project's reliable bald-character tell — the identity-pair floor
dropping an order of magnitude, because the dither *is* the grooms — lived
in prose while the report carried no floor field at all, so nothing could
fail on it. **A documented tell is a note; a control is a field in the
report that a run can fail on.**

## Evidence rules

Name both verdicts, separately, in every claim about a run. Write
"EXECUTION clean, OUTPUT `<instrument>` = `<number>` against
`<threshold>`", never "the run passed". An OUTPUT check that has never
failed on this project is unproven, not strong — say so where you cite it.
Record in the run's own report: the instrument's number per partition, the
partition spelled out, every threshold and which side the number fell on,
the census integers, and the resolved manifest for every chain.

Related: `prove-an-instrument-can-fail` for whether the OUTPUT instrument
can see anything at all; `establish-a-noise-floor` for the unit an OUTPUT
number is cited in; `write-a-run-sidecar` for recording the parameters both
verdicts were about.

## Provenance

Five sentinel-green failures in one character-project corpus (2026-07/08),
including the tick-driven sun and the fallback-checker garments that
survived four grade rounds. Generalized 2026-08-12 from that project's
full-detail original.

## Changelog

- 2026-08-12 — Initial generalized port.
