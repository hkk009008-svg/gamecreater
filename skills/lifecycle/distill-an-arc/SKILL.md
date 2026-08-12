---
name: distill-an-arc
description: The arc-end pass that turns raw inbox lessons into skill edits without degrading the corpus — sweep, dedupe, propose with evidence, apply on the user's go, changelog everything. Use when an arc closes, and never mid-task.
---

# Distill an Arc

This skill grants no skill-edit authority by itself; the edits it proposes
are applied only on the user's go.

## When

An arc's phase-change signal has fired — a candidate froze, an approach
died, the feature shipped — and the lessons inboxes have entries since the
last distill. This is the ONLY time skill bodies change. Mid-task skill
editing is the sediment route: rules written while the failure is fresh
are vivid, specific, and half-digested, and a corpus full of them stops
being trusted or read.

## The pass

1. **Sweep** both inboxes (harness-general and the game's own) for entries
   since the last distill marker.

2. **Dedupe against the corpus.** Most entries are instances of a rule
   already encoded. For those: mark the entry `[distilled → skill-name]`,
   and at most sharpen the existing skill's example if the new instance is
   stronger than the one it carries. An instance is not a new rule.

3. **Triage the genuinely new.** For each, decide and record:
   - **Edit an existing skill** — the pattern extends a rule that exists.
   - **New skill** — rare. It must name the failure that paid for it, and
     the failure must be one a future session could plausibly repeat. A
     rule without a named failure is an opinion and stays in the inbox.
   - **Reject** — recorded with a reason, so the question doesn't reopen
     every arc.

4. **Propose to the user**: the list of edits, each with the inbox
   entries and evidence behind it, sized so one "go" can cover the batch.
   Apply only on that go.

5. **Apply and changelog.** Every touched skill's `## Changelog` gains a
   dated line naming the change and the entries that forced it. Provenance
   chains stay reconstructible: entry → evidence → edit.

6. **Verify the corpus stays loadable**: run the skill-surface sync check
   and the publishability scrub. A skill grown past a screen of text is a
   split candidate — a skill that isn't loaded teaches nothing.

7. **Mark the distill** in each inbox (date + last entry covered), so the
   next sweep has a start line.

## Quality bars, each from a measured failure mode

- **Every rule names its failure.** The corpus this system inherits from
  proved the value: skills whose every section cites a paid-for instance
  get followed; advice that is wrong in the common case gets discarded the
  first time it is inconvenient.
- **Wrong diagnoses distill too.** A corrected diagnosis left uncorrected
  becomes corpus — record it as wrong in the skill's example, not just
  deleted.
- **Instruments convicted as blind go in the register**, not the skill —
  the known-untrusted list is the game's, the pattern (if one exists) is
  the skill's.
- **Retire, don't delete.** A skill whose rule stopped being true gets a
  tombstone naming what replaced it; git history keeps the body.

## When the user is not available

The sweep and triage can run; the proposal waits. Never let "the arc ended
and nobody said go" quietly become "I applied them anyway" — an unapplied
proposal is a fine thing to carry in NOW.md.

## Provenance

Shaped by the two bounding failures of the originating corpora: a week of
pipeline lessons stranded in an unversioned notes file (leak), and the
studied failure mode of reflexive per-session skill updates degrading a
corpus (sediment) — plus the measured success of failure-cited skills
being the ones that actually got followed.

## Changelog

- 2026-08-12 — Initial authoring.
