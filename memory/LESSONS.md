# Lessons inbox — harness-general

Append-only during work; distilled into skills only at arc end
(`distill-an-arc`). One entry per lesson: date, what happened, the rule it
suggests, evidence ref, candidate skill target. Game-specific instances
live in the game's own inbox; entries here are the generalized pattern.
`[distilled → skill]` marks entries already encoded; they stay as
provenance.

---

- 2026-08-12 — A verification gate ran the editor's play-in-editor path on
  a hand-opened map and passed for days while the user's real sessions
  failed. Real entry differs on four axes: map actually booted, fresh
  class-spawn vs patched instance, spawn point, cold load vs in-session
  state. Rule: gate on the consumer's actual entry path.
  `[distilled → verify-on-the-real-entry]`

- 2026-08-12 — Fixes applied to a placed actor instance were invisible to
  every fresh spawn of its class; the player's entry spawns fresh. Rule:
  fix class templates, verify on a fresh spawn after cold reload.
  `[distilled → verify-on-the-real-entry]`

- 2026-08-12 — In-session Blueprint compiles reported healthy while the
  saved bytes failed compile on every cold load, cascading a vendor error
  into the player pawn falling back to parent defaults. Rule: a compile
  claim needs a fresh-process load; "compiles now" ≠ "loads clean".
  `[distilled → verify-on-the-real-entry]`

- 2026-08-12 — Engine config array lines written without the `+` prefix
  silently replace each other; only the last survived, which unregistered
  an enum and broke every Blueprint pinned to it. Rule: repeated config
  keys need `+`; after any config edit, re-verify the consumers.
  `[distilled → edit-vendor-data-headlessly]`

- 2026-08-12 — Select-node pins on a config-registered enum bind by enum
  VALUE, not display name: registering the right names at wrong slots left
  errors; registering the exact slots cleared them regardless of names.
  Rule: recover the original value layout from the asset's own name table
  before guessing registrations. `[distilled → edit-vendor-data-headlessly]`

- 2026-08-12 — A no-op round-trip gate (export → rebuild → compare before
  any real write) caught three distinct corruption traps in one table
  pipeline: unregistered tags nulling out, display-name enum imports
  resetting values, and unanchored field regexes shadowing prefixed
  fields. Rule: never write a rebuilt asset until the identity rebuild is
  byte-equivalent. `[distilled → edit-vendor-data-headlessly]`

- 2026-08-12 — Two cycles were lost guessing scripting-API property names;
  one cycle of harvesting candidate strings from the asset binary and
  battery-testing them against live objects found the real names (some
  with trailing spaces). Rule: harvest and test, never guess names.
  `[distilled → edit-vendor-data-headlessly]`

- 2026-08-12 — Twice, the decisive evidence for a works-here-fails-there
  bug was a screenshot of the user's live session (an error banner and a
  fallback pawn visible only there). Remote clicks failed (DPI mismatch)
  but screenshots worked. Rule: look at the user's actual screen before
  theorizing about their environment. `[distilled → watch-the-live-session]`

- 2026-08-12 — Overlap-triggered pickups no-op when the player spawns
  already inside them: the overlap fires before inventory init. Rule:
  place spawn-adjacent interactables a couple of steps away; test the
  walk-on, not the spawn-on.

- 2026-08-12 — Creating an asset at a path where one was deleted earlier
  in the same editor session fails; reusing the existing asset works.
  Rule: prefer reuse-or-edit over delete-recreate within a session.

- 2026-08-12 — A week of hard-won pipeline lessons lived in a notes file
  inside a gitignored experiments directory — unversioned, one disk
  failure from gone. Rule: lessons land in a versioned inbox the moment
  they are paid for. `[distilled → this repo's memory doctrine]`

- 2026-08-13 — Both "proven live" guards were dead on the next session: the
  hook command used cmd-style `%CLAUDE_PROJECT_DIR%`, and this session's
  harness runs hooks under a POSIX shell where that is a literal — every
  shell call failed closed on a missing-file error. The earlier proof had
  exercised the scripts' exit codes, not the settings→shell→script wiring.
  Rule: prove a control through the exact wiring the real threat uses, and
  re-prove it when the executor changes; write hook commands in
  executor-agnostic form (`${CLAUDE_PROJECT_DIR:-.}` with forward slashes —
  hook cwd is the project dir as fallback). Evidence: this session's
  PreToolUse errors, then a fake `git push` blocked through the new wiring.
  Candidate skill target: prove-a-control.

- 2026-08-13 — A publish gate scrubbed every blob in every rev and passed
  while the user's personal email rode along in the author/committer field
  of every commit — a channel a tree scrub structurally cannot see. Caught
  only because the pre-flip audit swept the whole publishable surface:
  blobs on all refs, commit metadata, ref inventory, platform surfaces
  (issues/wiki/description). Fixed by rewriting all commits to the GitHub
  noreply identity before the flip (trees proven byte-identical). Rule:
  "scrub is clean" covers a tree; publishing exposes a surface — audit the
  surface. Candidate skill target: probe-a-claim, or a new
  publish-a-repo skill.

- 2026-08-13 — The scrub gate goes green vacuously: with `git ls-files`
  failing (e.g. run outside a repo) it prints "scrub clean: 0 tracked text
  files" and exits 0, and with the gitignored scrub_terms.local.txt absent
  (any fresh clone) it silently degrades from 24 patterns to 7 — it only
  refuses at zero patterns. Rule: a green verdict must carry its
  denominators (files scanned, patterns loaded) and refuse or warn when
  either collapses. Evidence: auditor ran scripts/scrub_check.py in a
  non-git dir → "scrub clean: 0 tracked text files, 7 patterns", exit 0.
  Candidate skill target: prove-an-instrument-can-fail; concrete fix
  spawned as a follow-up task.

- 2026-08-13 — The scrub-hardening branch arrived 47-green with a claimed
  real-entry check, yet `python scripts/scrub_check.py` crashed on this
  machine: every test drove main() in-process against a StringIO, which
  never encodes, while the real console encodes cp949 and died on em-dash
  message text — collapsing "warning" into exit 1, the code that means
  "hits found". Same class: an unlaunchable git binary tracebacked into
  exit 1 too. Fixed with subprocess TestRealEntry tests (red first on this
  machine), ASCII verdict text, a backslashreplace stdout fallback, and
  exit-2 on enumeration launch failure. Rule: a gate's consumer entry
  includes the console codepage it prints under; in-process green proves
  logic, not the instrument. Candidate skill target:
  verify-on-the-real-entry (generalize beyond gameplay to instruments).
