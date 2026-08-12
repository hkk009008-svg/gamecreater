---
name: probe-a-claim
description: Formation-time discipline for load-bearing claims — derive the premises from the claim's shape, cite each with the command that measured it, attack it with a reduced-context reading, and record the blank cells. Use BEFORE writing "verified", "enforced", "complete", "never", "measured", or citing a reference as provenance; prove-a-control is for the mechanism, this is for the belief.
---

# Probe a Claim

## Why this exists
Nine defects in one session had one mechanism: the author verified the
property they were thinking about, not the property the claim rested on.
"Enforced pre-dispatch" — correct check, nothing called it. "Measured" — only
in the author's checkout. "This ref anchors the report" — well-formed,
resolving to nothing. Every miss was one command from detection, and a reader
holding only the claim caught all nine, because it never made the assumption.
The failure is circularity at belief formation: the claim and its check both
derived from the same artifact, so their agreement carried no information.
The remedy is otherness — from the claim's shape, from a reduced-context
reader, from an exit code — none sourced from the author's recall, because
recall is the broken faculty.

## The loop, per load-bearing claim

1. **Premises from shape, not memory.** The claim's own vocabulary names its
   premises. "Enforced" ⇒ something invokes the check on the governed path.
   "Measured" ⇒ an instrument ran, here, and its output exists. "Complete" ⇒
   the population was enumerated and the count of examined vs. total is
   stated. "Never / always" ⇒ the space was generated, not sampled.
   "Reference X" ⇒ X resolves AND is the document claimed. You can forget a
   premise; you cannot forget the shape of your own sentence.

2. **Cite each premise with an instrument.** A citation is a command plus its
   real output — never prose. Tag provenance: MEASURED, RELAYED, REMEMBERED,
   INFERRED. A load-bearing premise resting on the last two is a blank cell
   wearing a label.

3. **Run the one embarrassing command.** Before writing the claim as fact,
   ask "what single command would most embarrass this?" and run it. Every
   failure this skill encodes was one command away.

4. **Attack it with a reduced-context reading.** Hand ONLY the claim sentence
   — never the code, the diff, or your reasoning; context is contamination —
   to a reader that hasn't made your assumptions: a fresh session, a
   subagent given the bare sentence, or at minimum yourself re-deriving the
   premises cold from step 1 before looking at your evidence table. The
   value is otherness: a reader that never saw the artifact cannot agree
   with it by construction.

5. **Record, so the blank cells exist.** Keep a claim table in the arc's
   evidence: claim, premises, citation per premise, provenance tag, and the
   kill attempted. Unexamined premises are written ASSUMED — visible, not
   silently absent.

## What counts as a kill
An attempt to make the claim fail while believing it true: delete the call
site, restore the defect, run the divergent input, feed the parser the case
your pattern assumes away. Confirmations by the claim's own author agreeing
with the claim's own artifact count zero — same source, no information.

## A hedge you wrote is an unrecorded ASSUMED row

A doubt you can write down is a premise you already know is unverified —
writing it is the timestamp, not the discharge. Before submitting anything,
sweep your own outgoing text for hedge vocabulary — "possibly", "may be",
"I suspect", "should probably" — and give each the treatment any premise
gets: resolve it with an instrument, or record it as ASSUMED so the blank
cell is visible instead of shipped. Measured: a hedge shipped in an author's
own review brief came back as a MAJOR finding one round later.

## Division of labour
- `probe-a-claim` — the *belief*: what must be true, who checked, who
  disagreed.
- `prove-a-control` — the *mechanism*: reversion and evasion controls on
  guards.
- Neither substitutes for the non-author review an accepted result needs.

## Honest limits
- The premise shapes cover the measured failures; a failure of a new shape
  will not be named until someone adds it — extend the list when one lands.
- The claim table is self-reported. It catches what you wrote down, not what
  you didn't; the reduced-context attack is the one step sourced from
  outside, so skipping it collapses the loop back to one party.

## Provenance

Nine defects in one session (2026-07-26/27) with a single mechanism —
verifying the property in mind rather than the property claimed — each one
command from detection. Ported from the originating governance corpus
2026-08-12; that corpus's executable claim-ledger tooling is replaced here
by the arc-evidence claim table, keeping the loop portable.

## Changelog

- 2026-08-12 — Initial port; repo-specific claim-ledger commands and
  provider-probe machinery generalized to a reduced-context reading + claim
  table. All premises-from-shape, kill, and hedge rules kept.
