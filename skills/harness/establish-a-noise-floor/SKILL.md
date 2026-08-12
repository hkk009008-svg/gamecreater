---
name: establish-a-noise-floor
description: Give every render delta a unit by measuring a same-configuration repeat pair in the same run. Covers the borrowed floor that manufactures a phantom effect, the suspiciously low floor that means the subject is gone, the whole-frame floor that hides a small object, and simulation noise read as signal. Use before reporting any pixel delta as an effect, or dismissing one as below the floor.
---

# Establish a Noise Floor

This skill grants no engine-launch, canonical-write, or external-effect
authority.

## When

You rendered two configurations, measured a pixel difference, and are about
to call it an effect. A delta is a bare number until it is divided by the
run-to-run difference of the *identical* configuration, measured in the
same run. Shoot the same frame twice, changing nothing, and diff it —
before you read anything else.

Bracket the run: floor frame shot first, floor frame shot last, same
parameters; the delta between those two is the run's unit. If the rig has
no measured floor yet, spend a batch of consecutive captures of one frame
and plot max delta against index — that one sweep yields the warm-up count,
the threshold for every other gate, and a permanent determinism regression
test.

## The floor is the unit, and anything at 1.0x floor is nothing

Measured: under FXAA, two identical frames of a groom character differed at
mean 4.02/pixel with 27% of pixels off by more than 8 — every subtle
parameter step in that sweep landed below it; all noise. The same
discipline in percent-of-pixels units on a dressed character: determinism
floor 0.256%; a real cloth-map effect measured 11.5x that; a hem mask
measured 1.09x — indistinguishable from noise despite provably landing in
the asset. Report effects as multiples of the floor, never as bare
absolutes, and treat anything under ~1.5x floor as unproven.

## A floor borrowed from another configuration manufactures results

A close-up signal quoted against the full-view floor read 1.98x —
"close-up nearly doubles separation" — and was published. Against its own
floor it was 1.66x, i.e. nothing; the conclusion had to be retracted.
Re-measure the floor whenever render size, quality level, LOD forcing,
view, or component set changes — each moves the floor further than most
real effects.

## Distinguish settling from dither by re-running, not by the number

A settling floor is transient and will not reproduce; a dither floor is
stationary and reproduces to four significant figures. A floor that jumped
after a quality change reproduced as 2.7532 then 2.7526 — dither, from
stochastic shading the higher tier enables. The same-parameter repeat is
the cheapest instrument in the set and the one most often skipped, because
it can only ever say "you found nothing."

## Turn the stochastic subsystem off for the pair, or it invents the effect

A parameter diff taken with cloth simulation enabled reported tens of
thousands of changed pixels; the identical comparison as a deterministic
pair with the solver off gave zero. Distinguish a physical effect from
solver reseeding by disabling the simulator and re-rendering — never by
raising the threshold. A threshold lifted until it clears the noise field
also clears every real effect under it: one false positive becomes a
permanent false negative.

## A suspiciously LOW floor is a red flag, not good news

A floor an order of magnitude below the known-good value was a completely
missing subject: the dither *was* the grooms, so losing them removed the
only stochastic source in frame. Check subject-presence reads before
celebrating a low floor. The pair is structurally blind to any defect that
reproduces — two identically wrong frames measure 0.000 and pass as
perfect determinism.

## A high floor invalidates the run in both directions

A floor once recorded as "per-pixel groom dither" was actually async
compilation still in flight: with a fully warm cache the same pair measured
0.000 byte-identical. So a signal dismissed as "below the floor" is
**unproven, not disproven** when the floor was inflated — re-test it warm.
And a floor pair that disagrees with the previous run's voids the run: say
so and rerun; do not mine it for the one comparison that looks plausible.

## Restrict the metric to the object's region, and the control with it

An object occupying a fraction of a percent of the frame cannot move a
whole-frame statistic: a correct grade measured below the global floor
whole-plate and 7x floor inside the object's region — where the control
read 0.00%, because the simulation noise driving the global floor never
reaches that region. A floor is a property of **(configuration, region)**;
moving either coordinate without re-measuring converts a measurement back
into an argument. Carry a local-window statistic beside every global mean.

## Read the shape of the deltas to name the failure

| What you see | What it is |
|---|---|
| Same mean delta for every pair regardless of which knob moved | dither noise; no parameter reached the pixels |
| Exact byte identity between shots with different parameters | state never changed, or the frame was not re-rendered |
| Uniform low mean with a hard low max, nothing above ~20 | empty frame — the subject did not render |
| One delta well above the floor, others at the floor | the effect is real and localised to that knob |

When *nothing* clears the floor — including comparisons that obviously
should — stop computing and open one frame. A whole-frame mean cannot tell
you the subject is missing; your eyes can, in a second.

## Evidence rules

State the floor alongside every delta you cite; a delta quoted against a
floor from a different configuration is worse than unreadable, because the
wrong multiple is confident. If a control ran and the effect did not clear
the floor, that is a finding — the knob does not do what its name suggests
in this configuration — not a null result. Record in the run's report: the
floor pair's shot names and delta; the metric and exact region; the control
in that same region; render size, AA method, quality, LOD forcing; which
stochastic subsystems were on; and the hardware bucket key. A floor whose
configuration was not recorded cannot be compared with any other floor.

Related: `prove-an-instrument-can-fail` for forcing a detector to fire
before trusting a null; `separate-execution-from-output` for why PASS kept
printing while the floor pair said nothing rendered; `write-a-run-sidecar`
for the artifact that carries these fields.

## Provenance

The retracted 1.98x conclusion, the solver-reseed false positive, the
bald-subject low floor, and the async-inflation misread are all measured
instances from one character-project corpus (2026-07/08). Generalized
2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
