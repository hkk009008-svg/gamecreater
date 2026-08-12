---
name: isolate-a-variable
description: Decide what to measure when a mechanism works in setup X and fails in setup Y — a trigger and threshold for batching candidate differences into one run instead of serializing guesses, the reads that make a matrix readable, and why a zero is a claim needing its own known-positive. Use on works-here-fails-there failures, on any measurement that reads zero or unchanged, and when a documented precedent makes one suspect obvious.
---

# Isolate a Variable

## When
Something works in setup X and fails in setup Y and you are about to say why.
Also when a measurement comes back zero, unchanged, or clean — "the effect is
absent" and "the instrument is blind here" produce identical evidence.

`prove-a-control` is for the mechanism, `probe-a-claim` is for the belief.
This is for the **cause**.

## The rule, with its threshold

Before testing your top hypothesis, spend five minutes writing candidate
differences **and, beside each, the read that would discriminate it**. Then:

- **Three or more candidates still plausible, and the discriminating reads
  are cheap and non-perturbing** → batch them into ONE run. Serializing
  guesses here is what costs real money.
- **One dominant candidate with a genuinely cheap test** (a one-command diff,
  an env dump) → just run it. Hypothesis-first costs `c + (1−p)·M` against the
  matrix's `M`, so with a strong prior and a cheap test it wins on arithmetic.
  A failed direct test is not waste — it is one matrix cell bought at cell
  price.
- **Y is not reproducible on demand** (a customer box, a six-hour state, a
  live incident) → you get few observations; spend them on discriminating
  reads, not on confirming a favourite.

**Stopping rule for the list:** stop when every remaining candidate has a read
next to it. A candidate you cannot discriminate is not on the list, it is an
admission — write it down as unexamined rather than letting its absence read
as absence of the cause.

This does NOT say "always build a matrix". Unconditional matrix-first is
arithmetically wrong whenever the prior is strong and the test is cheap.

## "Every difference" is a lie you tell yourself

You cannot enumerate every difference between two real setups — the gap
between a laptop and a CI runner is kernel, libc, locale, PATH order, umask,
clock, DNS, cached layers, seeds, and the whole environment block. What you
actually write down is *the differences you thought of*: a hypothesis set
with extra ceremony.

That matters because **an unlisted difference produces no cell and therefore
no evidence of its own absence.** A green matrix is not proof the cause is
outside it. Say which differences you enumerated, and treat the list as
provisional.

The failure mode is not "I had no hypothesis." It is "I had a good one
immediately." A suspect with a **documented precedent is the most dangerous
kind**, because the precedent supplies the confidence a measurement should
have supplied. Measured: an animation drive worked in an editor world and
failed in a capture harness, and the corpus already recorded a tick-dependent
actor failing in exactly that path — so that difference was convicted on
circumstantial evidence and three runs of patches aimed at it fixed nothing.
One run putting the same rig through both setups returned bit-identical
results; the real variable was the component class, which had never been on
the list. **The winning column was added on the second pass — the enumeration
was incomplete, exactly as this section warns.**

**Rule:** a prior that explains the symptom is a reason to test that
difference first, never a reason to skip testing it.

## Reads are where the banished hypothesis re-enters

Picking reads IS hypothesis selection, so pick them for coverage of failure
*modes*, not to confirm a story:

- Two or three **independent** witnesses — different mechanism, not different
  formatting of the same number.
- **Run the known-positive arm first.** It calibrates every read. Without it a
  silent read is unattributable.

| speaks in X | speaks in Y | conclusion |
|---|---|---|
| yes | yes | that difference is not the cause — cross it off |
| yes | no | convicted *by this read*, pending mechanism confirmation |
| no | no | **the read is blind** and says nothing about anything |

The bottom row is what saves you. A read silent in both setups, kept as sole
witness, would have "confirmed" any story asked of it.

## Four ways the matrix lies

1. **Interactions.** A cause needing A∧B leaves a one-factor-at-a-time grid
   all green — a confident false negative. If single factors come back clean,
   suspect a pair before you suspect the list.
2. **Flakiness.** One observation per cell is a sample, not a measurement.
   Repeat per cell or state plainly that the cells are single-shot.
3. **Perturbation.** Adding reads can be what makes Y stop failing. Prefer
   non-perturbing witnesses; if you cannot get one, say the observation is
   load-bearing on the instrument.
4. **Correlation, not mechanism.** A red column localizes; it does not
   explain. Confirm by making the mechanism fail and recover on demand —
   that hands off to `prove-a-control`.

## A zero is a claim, and needs the same proof as a one

"No vertices moved", "no pixels changed", "the count is clean" — each is
either absence of the effect or blindness of the instrument, and nothing in
the number distinguishes them. Both have shipped:

- A component-level morph read reported 0 vertices moved at full weight. The
  morph was fine; the read path was morph-blind. It nearly convicted a
  working asset.
- A window-count read gave ~96% background inside a defect box BOTH before
  and after a geometry fix — the sightline exited onto a near-black surface,
  so dark-on-dark matched within tolerance either way.

**Rule:** before reading a zero as absence, produce a known-positive on the
SAME instrument at the SAME location. If you cannot make it speak where you
are asking, you have no measurement there — say so and move the question to
an instrument that can.

## What to write down

Record the differences you ELIMINATED and the ones you never examined, not
just the one you convicted. Record wrong diagnoses as wrong — a corrected
diagnosis left uncorrected becomes corpus. Any read convicted as blind goes
in the register by name, so nobody cites it as a witness later.

**Do not claim the counterfactual.** "The matrix was cheaper than guessing"
compares against a branch nobody ran. Report what the chosen path cost and
what it eliminated; that is measurable, and the comparison is not.

## Provenance

Paid for across a character-pipeline corpus (2026-07/08): three runs of
patches aimed at a precedent-backed suspect that was innocent; a morph-blind
read that nearly convicted a working asset; a dark-on-dark window count that
could not distinguish open from closed. Ported from the originating
governance corpus 2026-08-12.

## Changelog

- 2026-08-12 — Initial port into the transferable corpus; provider- and
  project-specific machinery removed, all rules and measured instances kept.
