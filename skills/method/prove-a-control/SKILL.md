---
name: prove-a-control
description: Prove a guard, gate, or negative control actually holds before claiming it does — the two control kinds (reversion and evasion), the five ways a green control means nothing, and the evidence rules for citing it. Use when writing or reviewing any test whose value is that it would fail, any pre-dispatch or pre-spend gate, or any assertion described as "measured".
---

# Prove a Control

## When
You are about to say a guard holds, a gate is enforced, or a test proves
something. Also when reviewing someone else's claim of the same. A control's
whole value is that it would fail; a control that cannot fail is worse than
none, because a green one is read as proof.

## Run two controls, and do not mistake one for the other

**Reversion** — restore the defect and confirm the control fails *for the
right reason*, not by erroring a line earlier. Proves the control is not
vacuous.

**Evasion** — leave the control fully in place and try to reach the
forbidden outcome by another route. Proves the control is *sufficient*.

They answer different questions and reversion is the one you will remember
to run. Reversion structurally cannot catch a heuristic, because reverting
hands the control the exact shape it was written to recognize. In one
session three escapes passed reversion and died to evasion. If you find no
evasion route, say so — that is a finding, not an omission.

Restore every mutation from a byte snapshot and prove it with sha256 before
and after. Never restore from a moving ref. And defeat interpreter caching:
a byte-exact restore with colliding mtime and size replays the *mutant* from
stale bytecode — measured: the restored source passed as the mutated value
until mtime advanced one second. Run mutation matrices with bytecode writing
disabled and caches deleted between mutate and restore.

Pin each half of a paired defense separately. A mutation audit found ASCII
verdict text and an encoding backstop pinned only as a conjunction: either
half reverted alone with all 51 tests green; only both together were
caught. And test a flag's documented off-values, not just its on-state —
the one untested value (`"0"`) let a polarity flip that bricked the gate
survive the whole suite (2026-08-13 scrub-gate audit).

## Trap 1 — the control is correct but nothing calls it
Test the mechanism and never the wiring, and deleting the call site stays
green. Hit three times in one range: a gate no dispatch path invoked; its
replacement, whose tests drove the check directly; then the fix for *that*,
whose stub threw whatever it was handed, so dropping the argument still
passed. A check that is correct and is handed nothing checks nothing.

- Mutate by **deleting the call**, not by breaking the callee.
- Pin the call site separately: the caller refused, the side effect did not
  happen, and the *real arguments* arrived.
- Before writing "enforced on every X", grep for the caller.

## Trap 2 — an enumeration standing in for a property
A list of the cases you know about is exactly what a narrowing survives.
Three consecutive review rounds each named a form the previous list omitted.
Generate the space from the grammar, pin the property the list approximates,
and state in the test where the enumeration stops and why.

## Trap 3 — a text heuristic standing in for another language's semantics
Deciding what a parser, shell, or CLI *does* by pattern-matching its output.
Every hardening is another heuristic; delete the mechanism instead. Ask the
thing itself: feed the real input to the real parser and read its exit code.
Exit codes carry no text to misread.

## Trap 4 — a precondition inherited from the environment
A measurement that holds only where you ran it: cwd, checkout layout, a
machine-local config, a binary that happens to be on PATH. "34 passed" once
meant "on a host with the CLI installed". Manufacture the precondition
inside the test; do not gate on it — a gate leaves the measurement absent
exactly where the suite was red. Run it in both states.

Two more paid instances (2026-08-13): a hook command written in cmd syntax
(`%VAR%`) died silently when the next harness ran hooks under a POSIX
shell — a control is re-proven whenever its executor changes; and
gitignored config tiers (a push-grant file, local scrub terms) do not
follow a branch into a git worktree, so a guard that reads them holds
per-checkout — the same absence surfaced as a visible block in one gate
and degraded a sibling gate silently open. A guard that reads gitignored
config says which tree's config it read.

## Trap 5 — evidence that is well-formed and wrong
- **A reference that resolves to nothing.** Forty hex characters satisfy
  every shape check; three fabricated references were composed in one
  session. Verify a ref resolves **and is the document you claim** — read
  its first line.
- **Your own harness lying to you.** A stripped PATH once resolved an
  interpreter missing a stdlib module, and the failure was briefly reported
  as someone else's defect. Before reporting a measurement as a finding, ask
  what else your setup changed.
- **Prose no test can contradict.** Docstrings outlived their mechanism
  twice. If a comment states behaviour, pin the behaviour or delete the
  claim.

## A guard has two verdicts — prove the allow path too

Every wiring proof of one push-guard exercised the BLOCK path, so the
guard read as live while its allow path was broken in a dialect nobody had
tried: Git Bash wrote `/d/Unreal`, Windows Python could not use it as a
cwd, the visibility check never ran, and fail-closed blocked an authorized
push (2026-08-13). Right failure direction — and invisible until the first
authorized act used that form, precisely because blocks were the only
thing ever proven. Prove ALLOW live in every input dialect the tools emit;
a guard proven only by its blocks is half-proven.

## Fix the pattern, not the instance
A destructive fixture was fixed in one helper and reappeared in the next
fixture written *in the same commit*. Prefer exclusive creation over
check-then-act, and build a throwaway workspace rather than mutating the
checkout under review.

## Answering findings

Fix by subtraction converges; fix by addition reopens. Measured: one review
round returned 4 findings, its fixes added mechanism, and the next round
returned 6 — each addition was fresh attack surface. Before repairing
anything a finding names, ask what can be deleted instead, and say in the
commit which it was.

When your measurement disagrees with an independent reviewer's, re-measure
narrowly — change one variable — before defending. Session score when this
was written: reviewer measurement errors, zero; author self-inflicted
measurement errors, three. The burden of proof starts on the author's
harness.

## Before you say "verified"
- [ ] Reversion run; the control failed for the right reason.
- [ ] Evasion attempted; route found and closed, or absence stated.
- [ ] Call site mutated by deletion, not just the callee.
- [ ] Run in both environment states, not only the one you are in.
- [ ] Allow path proven in every input dialect, not only the block path.
- [ ] Paired defenses pinned per-half; documented off-values tested.
- [ ] Every cited command is one you actually ran, with its real output.
- [ ] Every reference resolves and is the document named.
- [ ] Limits you did not close are written down as limits.

Related: `probe-a-claim` for the belief upstream of the mechanism;
`create-regression-pin` for deferring a confirmed defect.

## Provenance

Every trap is a measured instance from the originating governance corpus
(2026-07): uncalled gates surviving three fix rounds, enumerations narrowed
three reviews running, text heuristics defeated by real parsers, fabricated
well-formed refs, stale-bytecode restores. Ported 2026-08-12.

## Changelog

- 2026-08-12 — Initial port; seat/review-protocol references removed, all
  traps, the subtraction rule, and the checklist kept.
- 2026-08-13 — Allow-path section, per-half pins and off-value rule, and
  the executor-change / worktree-gitignored-tier instances in Trap 4.
  Forced by: dead %VAR% hook wiring, the push-guard's /d/-path false
  block, mutation-audit survivors M4/M8/M9, and the worktree grant-file
  block (inbox entries of 2026-08-13).
