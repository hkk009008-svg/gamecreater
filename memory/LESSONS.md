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
  Candidate skill target: prove-a-control. `[distilled → prove-a-control]`

- 2026-08-13 — A publish gate scrubbed every blob in every rev and passed
  while the user's personal email rode along in the author/committer field
  of every commit — a channel a tree scrub structurally cannot see. Caught
  only because the pre-flip audit swept the whole publishable surface:
  blobs on all refs, commit metadata, ref inventory, platform surfaces
  (issues/wiki/description). Fixed by rewriting all commits to the GitHub
  noreply identity before the flip (trees proven byte-identical). Rule:
  "scrub is clean" covers a tree; publishing exposes a surface — audit the
  surface. Candidate skill target: probe-a-claim, or a new
  publish-a-repo skill. `[distilled → publish-a-repo]`

- 2026-08-13 — The scrub gate goes green vacuously: with `git ls-files`
  failing (e.g. run outside a repo) it prints "scrub clean: 0 tracked text
  files" and exits 0, and with the gitignored scrub_terms.local.txt absent
  (any fresh clone) it silently degrades from 24 patterns to 7 — it only
  refuses at zero patterns. Rule: a green verdict must carry its
  denominators (files scanned, patterns loaded) and refuse or warn when
  either collapses. Evidence: auditor ran scripts/scrub_check.py in a
  non-git dir → "scrub clean: 0 tracked text files, 7 patterns", exit 0.
  Candidate skill target: prove-an-instrument-can-fail; concrete fix
  spawned as a follow-up task. `[distilled → prove-an-instrument-can-fail]`

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
  verify-on-the-real-entry (generalize beyond gameplay to instruments). `[distilled → verify-on-the-real-entry]`

- 2026-08-13 — Adversarial acceptance on the hardened scrub measured the
  residual evasion surface on the real entry: (a) a tracked UTF-16 or
  early-NUL file carrying a real secret still exits 0 — the binary-skip
  heuristic drops it before scanning; it is counted as skipped, but an
  exit-code-only consumer would publish (planted AKIA key: rc 0; its
  ASCII twin: rc 1, same run). (b) The committed email regex backtracks
  quadratically on long @-less lines (80 KB → 35 s): one base64/minified
  tracked file degrades the gate to no-verdict. (c) With the local tier
  absent the gate scans 7 generic patterns and exits 0 — project-noun
  enforcement is opt-in; a publish flow must set
  SCRUB_REQUIRE_LOCAL_TERMS=1 to mean what "clean" implies. Rule: a skip
  tally in the output is not a skip tally at the consumer — decide per
  gate whether skipped>0 may still exit 0. Deferred as a spawned task;
  candidate skill target: prove-an-instrument-can-fail. `[distilled → prove-an-instrument-can-fail]`

- 2026-08-13 — The push-guard false-blocked an authorized push: the Bash
  tool wrote `git -C /d/Unreal push`, the hook handed the POSIX drive
  path to Windows Python as a subprocess cwd, gh never ran, and the
  fail-closed default read as "cannot verify visibility". Right failure
  direction, wrong verdict — and invisible until the first authorized
  push used that path form, because every earlier wiring proof used
  paths that were SUPPOSED to block. Rule: a guard's inputs cross shell
  dialects; normalize at the boundary (/d/... → D:/...), and prove the
  ALLOW path live in every dialect the tools emit, not only the block
  path. Fixed with red-first pins in test_hook_pretooluse.py.
  Candidate skill target: prove-a-control (allow-path proofs per dialect). `[distilled → prove-a-control]`

- 2026-08-13 — A mutation audit of a fresh 51-test suite found the two
  halves of a paired defense (ASCII messages + encoding backstop) were
  pinned only as a conjunction: either half reverted alone, suite green;
  both reverted, caught. Same round: the documented "0" off-value of an
  env flag had no test, so a polarity flip bricking the gate survived.
  Rule: when a defense is a pair, pin each half separately; when a flag
  documents an off-value, test the off-value. All three killer tests were
  run red against their exact mutants before landing. Candidate skill
  target: prove-a-control (mutation as the red-run for regression pins). `[distilled → prove-a-control]`

- 2026-08-13 — The push guard blocked a push the user had already granted:
  gitignored config (public-grant.txt, scrub_terms.local.txt) does not
  follow a branch into a git worktree, and the PreToolUse hook runs the
  worktree's copy of the preflight, which resolves the grant file against
  its own tree — so every worktree session starts with every gitignored
  tier absent. Fail-closed turned this into a visible block here, but the
  same mechanism degrades the scrub gate silently-open (7 of 24 patterns)
  in the same worktree. Rule: a guard that reads gitignored config must
  say which tree's config it read, and a worktree session must copy the
  gitignored tiers in (or point at the primary checkout's) before trusting
  any gate. Evidence: preflight exit 1 from the worktree with the grant
  line present in the primary root; exit 0 after copying the file in.
  Candidate skill target: verify-on-the-real-entry or prove-a-control. `[distilled → prove-a-control]`

---

DISTILL MARKER 2026-08-13 — everything above is swept: five skill
edits (prove-a-control, verify-on-the-real-entry,
prove-an-instrument-can-fail + game mirror, edit-vendor-data-headlessly,
isolate-a-variable) and one new skill (publish-a-repo), each changelogged.
The next sweep starts below this line.

- 2026-08-13 -- The distill's verify step caught a project noun already
  PUBLIC: a regression test carrying a literal working-root path was
  committed and pushed AFTER the checkpoint's strict scrub ran, so the
  changed tree was never re-gated -- the gate was sound, the ordering was
  not. Tip fixed to neutral paths the same session; the noun stays
  reachable in one historical public blob (weak signal: drive letter +
  engine-named dir, no game name; rewrite judged not worth it). Rule: a
  gate's verdict binds the tree it ran on -- any commit after the gate
  re-runs the gate before the push. Candidate mechanization: preflight
  runs the strict scrub when the push target is public/granted; awaiting
  the user's word.
