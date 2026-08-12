---
name: write-a-run-sidecar
description: Make every run's output carry the parameters that produced it, so a later comparison is a diff, not a reconstruction. Covers runs that cannot be placed on their own axis, reports written before the gates that fill them, digests pinned in prose, and the configuration key a reference image is meaningless without. Use before launching any run whose output will be compared to another run.
---

# Write a Run Sidecar

This skill grants no engine-launch, canonical-write, push, or spend
authority.

## When

You are about to launch a run and let the output directory name carry the
parameters. It will not: the name holds one variable, the log holds the
rest, and the log has a rotation policy. Write a JSON sidecar beside the
images, after the gates, and the run stays comparable for as long as the
images exist.

## A directory name is not a parameter record

Measured instance: a six-run lighting sweep encoded only the intensity in
its directory names; the aim lived in log stamps that had rotated away by
the time anyone asked. A reconstruction produced nearly inverted readings.
Those six runs are not wrong but **unplaceable**, which is worse: a wrong
number can be corrected, and an unplaceable one has to be re-earned at
full sweep cost. Distinguish a recoverable run from an unplaceable one by
deleting the log directory in your head — the report looked complete and
every field in it was correct; the one field that mattered wasn't in it.

## The fields a first draft drops are the last three

The proven minimum set: every varied parameter by name, **harness content
hash**, changed-line count against the committed state, capture size.

- **harness hash** — the run is a function of the script, not only of its
  arguments. Without it, two runs one commit apart diff as if the code had
  been fixed.
- **changed-line count** — a hash says *different*; a count says *how
  much*. It catches "I patched the harness between the two runs I am about
  to compare."
- **capture size** — a noise floor is per-configuration; a signal quoted
  against another size's floor has already produced a published-then-
  retracted conclusion. Recording the field turns that from something you
  must remember into something a comparison can refuse.

## Write the report after the gates, and never let an unrun gate write `[]`

Measured: a report written *before* its light census ran showed an empty
lights list on a build whose light gate had passed. Two rules, the second
surviving the refactor that reintroduces the first: (1) the sidecar writer
runs **last** — every gate contributes to an in-memory dict, one write at
the end; (2) a gate that did not run writes `null` — never `[]`, never 0,
because an empty list is indistinguishable from a measured absence.

## Record fields nobody asked for — the diff answers a query you never wrote

A light-census field paid for itself on its first run by exposing an
election flip previously readable only in engine source. And its limit: **a
recorded field is a measurement and inherits its instrument's blind spot** —
the same census recorded a confidently wrong light count for months
because its query was structurally blind to one component class. Writing a
number down does not validate it; see `prove-an-instrument-can-fail`.

## Provenance belongs in the artifact, never in the prose

A hash written into prose goes stale silently — during one review pass the
harness digests changed four times. The rule that held: no digest in prose;
every run stamps into its own report the digest it actually used. The
clearest exemplar is a config file carrying its own delta, source hash, and
rollback pointer inline — an artifact that names what produced it and what
restores it needs no external index to stay true.

## A recorded hash that nothing verifies is provenance, not a guard

Measured: ten sidecars carried harness digests that no longer matched the
files they named, and zero runs failed — nothing read the hash back. The
cheap upgrade is not a hash check at launch but a **comparison gate**:
refuse to diff two runs whose sidecars disagree on harness hash, capture
size, or bucket key, printing both values. Gating the launch stops work;
gating the comparison stops the only thing a mismatch can actually corrupt.

## A golden is (image, config), not image

Engine screenshot-comparison frameworks bucket baselines by
platform/RHI/shader-model; browser-world golden systems key by OS, GPU,
and driver. Both concede the point: a reference image is a reference for
exactly one configuration. Record GPU, driver, RHI, shader model, and
engine version in every capture's sidecar **before there is a second
machine** — after the first driver upgrade there is no way to separate
references legitimately invalidated from ones merely re-bucketed. A
single-workstation project has exactly one bucket, which is why the field
costs nothing today and cannot be back-filled tomorrow.

## Write it atomically from a fixed schema

A half-written sidecar is worse than a missing one, because the missing
one is visibly missing. Atomic JSON (exclusive-create + rename), a
manifest hash per attempt, interpreter and package provenance recorded.
**Record a fixed environment tuple, not the whole environment** — the
handful of variables that change the numbers (hash seed, thread counts,
bytecode flag). A full env dump churns every run, turning every sidecar
diff into noise, and copies whatever the shell held into a file you may
share.

## Record what produced the artifact, not that it ran

The sidecar sits beside the output it describes, written once, last, after
every gate. PASS is not one of its fields — see
`separate-execution-from-output`. Minimum: every varied parameter
(defaults included — a default is a parameter), harness hash +
changed-line count, capture size and this run's identity-pair floor, the
bucket key, one block per gate with `null` for unrun, the fixed
environment tuple. A run whose parameters were not written beside its
output cannot be compared — and the cost is never that run, it is every
later run that wanted it as a baseline.

Related: `establish-a-noise-floor` for the floor the capture-size field
protects; `separate-execution-from-output` for why the sidecar carries
evidence and never a verdict.

## Provenance

The six unplaceable sweep runs, the empty-lights-list report, and the ten
stale-digest sidecars are measured instances from one character-project
corpus (2026-07/08). Generalized 2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
