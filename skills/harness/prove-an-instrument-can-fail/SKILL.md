---
name: prove-an-instrument-can-fail
description: Turn a null into evidence by proving the detector could have said something else. Covers controls that fire on purpose in the same run, filters structurally blind to a whole class, error strings that compare equal and read as unchanged, thresholds below the sampling scale, and reports that discard acquittals. Use before writing "no change", "nothing found", "clean", or "0 results".
---

# Prove an Instrument Can Fail

This skill grants no engine-launch, asset-write, or external-effect
authority; the scratch assets its controls write are separately authorized.

## When

You are about to write "no change", "nothing found", "clean", or "0
results" and treat that as a result. *A detector that cannot see a change
reports absence perfectly.* Every null in the originating corpus that
turned out to be a broken instrument looked exactly like a null that was
true. Before the null leaves the session, make the instrument say something
else on purpose, in the same run.

## Make the detector fire on purpose in the same run

A dry-run probe reported four clean trues — wrote nothing, dirtied nothing,
gate fired. The trues are not the evidence. The evidence is that in the
same run a deliberate mutation of a disposable scratch asset made the
dirty-package detector name it, and a rewritten scratch file made the
size+mtime detector name that. **Both fired.** Without them the trues are
indistinguishable from a broken probe. Report, do not raise, on the
positive hit — raising turns the measurement into a gate and loses the
answer. Clean up scratch in a `finally`, with per-run suffixes: the first
version of one such probe cleaned up on the happy path only and left three
scratch assets behind — the exact failure shape it was testing for.

## An instrument blind to a whole class still reports a confident total

A light census recorded "1 directional, 7 point" for months. Re-measured in
the world that actually renders: 12 lights, 2 directional, 9 point, 1
skylight — because the query used a component-class filter whose class is a
*sibling* of the skylight's, so it was structurally incapable of seeing
one, and **every instrument shared the filter, so none could corroborate
the others**. The same call also returned only the FIRST match under a
docstring promising "every light". And fixing a filter installs the next
blind spot: a reviewer predicted the corrected filter would collide with a
label heuristic, and the next run printed exactly that collision. Two
instruments that share a filter are one instrument; when two are supposed
to corroborate, prove they can disagree.

## An observer that mutates is not an observer

One "getter" stored a synthesized label on unlabelled actors as a side
effect; one property write triggered a re-stream that moved the readiness
floor — the act of measuring moved the thing measured. Before citing a
probe as read-only, check every accessor for a create-if-missing side
effect, and cite the check.

## Two identical error strings compare equal and read as "unchanged"

A round-trip profile stored an error string for a count on both sides and
reported the count unchanged; the same shape once reported an 89.9% match
by diffing an error message with itself. And asking for element *n* of a
single-element collection silently returned element 0, so an
increment-until-it-breaks loop reported 8 reachable levels on a mesh with
one. Assert well-formedness before the diff, never by the diff.

## A threshold below the sampling scale decides nothing

A duplicate-geometry detector convicted a garment with a residual threshold
sitting *below* the mesh's vertex spacing — at that scale the probe could
not have decided either way, and synthetic slabs at every plausible offset
were all convicted. **Validate a detector against synthetic positives AND
synthetic negatives before running it on the subject.** What settled the
question was a quantity neither probe computed: face-normal antiparallelism
at a constant gap.

## A report that discards acquittals cannot support a negative claim

The same probe wrote only convicted pairs into its report — the negative it
produced carried no margin at all — and it pre-filtered 97.8% of the
population before measuring anything. A null over 2.2% of a population,
with the acquittals thrown away, is not a null. Emit every comparison with
its margin, and the examined count beside the population count.

## A green verdict carries its denominators, and refuses when one collapses

A publishability gate printed "scrub clean: 0 tracked text files" with
exit 0 when its file enumerator failed outside a repo, and silently ran 7
of 24 patterns whenever a gitignored term tier was absent — every fresh
clone got the degraded instrument with the same green (2026-08-13). And a
tally inside the output is not a tally at the consumer: skipped files
were honestly counted in the summary line while an exit-code-only caller
published anyway — a planted key in a UTF-16 file rode through at rc 0
beside its ASCII twin caught at rc 1 in the same run. Denominators
(files scanned, patterns loaded, files skipped) belong in the verdict
line; any of them collapsing is a refusal with its own exit code, never a
clean; and a gate that can hang on pathological input returns no verdict
at all — bound its work per item.

## A sweep over an inert variable returns clean, identical, meaningless rows

N conditions come back clean and identical and the natural reading is "must
be a combination" — which spends the next day sweeping a variable that
never moved. A planned 12-launch sweep was cancelled by a two-point control
costing one launch: the stored constraints produced zero movement at all,
and the second point — a deliberate large change through the same path —
produced huge movement, proving the instrument reports change when there is
change. **Before sweeping N conditions, prove the instrument separates
known-good from known-bad, and prove the varied thing actually varies.**

## Run the untouched subject through the new instrument first

A jitter metric scored the *untouched* build above the reference — it was
picking up an unrelated silhouette feature. An instrument whose zero-point
is already worse than the target is a **relative** detector, usable for
gross overshoot and never as an absolute gate. That reading costs one run
and belongs before the instrument's first verdict, not after its first
surprise.

## Give a heuristic two derivations that must agree and a band it can refuse in

A "farthest vertex from centroid" landmark returned a wrist above the
elbow, and every downstream number was silently mirrored. The fix was not a
better heuristic: a second independent derivation, the two **required to
agree**, and an outright refusal band. A fallback only relocates the silent
wrong answer.

## State the scope in the verdict

A clean result is scoped to what the instrument measures, and the scope is
never in the verdict unless you put it there: a "no fragments" verdict
scoped to position and connectedness missed that the garment was a flat
ribbon; a vertex-extent read included orphan vertices that render nothing;
an island count measured index-connectivity, not position, so it was an
upper bound. Position plus connectedness is not shape; a summary statistic
is consistent with many stories.

## The cheapest control is the one that can only say "you found nothing"

A confound story was one edit from publication; testing it cost two minutes
and returned the same number as the identical-configuration repeat, on
every view, to three decimals — the confound was the instrument. Its
mirror: carry a negative control inside the same frame (pixels that must
NOT move, byte-identical across runs) beside every positive claim, and
prove a restore by re-rendering to a 0.0000 delta. At the far end, an
absurd positive control — a deliberately extreme input that must visibly
fire — is what distinguishes "the override was ignored" from "the override
was overwritten".

## Evidence rules

State the positive control alongside every null you cite; a null without a
control that fired is unreadable. Declare the blind spot in the report
itself, machine-readable — what the instrument measures, what it is
structurally blind to, and the control that would expose the blindness.
**An instrument with no declared blind spot is untrusted.** Record per
null: the control that fired, the query used verbatim, the threshold
against the sampling scale, examined vs population counts, and the reading
on the untouched subject.

Related: `establish-a-noise-floor` for whether a delta that DID appear
clears its floor; `separate-execution-from-output` for the verdict that
says the script ran and cannot see what it produced.

## Provenance

The sibling-class light census, the error-string self-diff, the
below-sampling-scale conviction, and the cancelled 12-launch sweep are
measured instances from one character-project corpus (2026-07/08).
Generalized 2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
- 2026-08-13 — Denominators section. Forced by: the scrub gate's
  vacuous-clean over zero files, the silent 24→7 pattern degradation,
  and the skipped-UTF-16-secret evasion (inbox entries of 2026-08-13;
  fixes red-proven in tests/test_scrub_check.py).
