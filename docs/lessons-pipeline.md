# The lessons pipeline — inbox → distill → changelog

How the system improves without degrading. Two failure modes bound the
design from opposite sides:

- **Leak** — lessons paid for in real time die in scrollback, gitignored
  notes, or "I'll remember." The next session re-pays full price.
- **Sediment** — every observation reflexively becomes doctrine; skills
  bloat with half-digested, sometimes wrong, rules; trust in the corpus
  collapses and it stops being read.

The pipeline is shaped so that capture is instant and cheap (defeating
leak) while promotion is deliberate and gated (defeating sediment).

## Stage 1 — capture (autonomous, immediate, raw)

The moment a lesson is paid for — a wrong diagnosis corrected, a trap
sprung, a cycle wasted — append one entry to the lessons inbox:

    - <date> — what happened, concretely. The rule it suggests.
      Evidence ref. Candidate skill target (or "none yet").

Harness-general lessons go to `memory/LESSONS.md`; game-specific instances
to the game's own inbox. No approval needed, no quality bar beyond
honesty: wrong diagnoses are recorded *as wrong*, blind instruments are
convicted by name, and negative results count. The inbox is evidence, not
doctrine — nothing in it binds a future decision.

## Stage 2 — distill (arc-end, deliberate, gated)

At each arc close, `distill-an-arc` runs:

1. Sweep both inboxes for entries since the last distill.
2. Dedupe against existing skills — most entries are instances of a rule
   already encoded; those get a `[distilled → skill]` mark and, at most,
   a sharpened example in the existing skill.
3. For genuinely new patterns, decide the target: an edit to an existing
   skill, a new skill (rare — it must name the failure that paid for it),
   or explicit rejection (recorded, so the question doesn't reopen).
4. Propose the edits to the user with the evidence; apply on their go.
5. Update each touched skill's `## Changelog` with date, change, and the
   inbox entries that forced it.

Skill bodies never change outside this stage. Mid-task, a skill found
wrong is *recorded* wrong (inbox + a note in the session) and current
code wins — the fix waits for the distill, when it can be judged cold.

## Stage 3 — verify the corpus stays loadable

After any distill: `sync_skills.py --check` (surface matches canonical),
and the scrub gate in strict mode:

    SCRUB_REQUIRE_LOCAL_TERMS=1 SCRUB_REQUIRE_TOTAL_SCAN=1 \
        python scripts/scrub_check.py

Strict mode is what makes "clean" mean it: `SCRUB_REQUIRE_LOCAL_TERMS=1`
refuses (exit 2) unless the project-noun tier actually loaded, and
`SCRUB_REQUIRE_TOTAL_SCAN=1` refuses if any tracked file was skipped or
any line truncated-scanned. Without the flags the gate degrades to the
generic patterns alone and tolerates skips — a publish must not
(2026-08-13 adversarial pass).

A skill that grows past a screen of text is a candidate for splitting —
discovery beats completeness, because a skill that isn't loaded teaches
nothing.

## Retirement

A skill whose rule stops being true (engine change, workflow change) is
retired to git history with a one-line tombstone in its category README
naming what replaced it. Retired ≠ deleted: the provenance chain stays
reconstructible.
