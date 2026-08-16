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

- 2026-08-13 -- System-integrity pass on this repo found the two mechanized
  guards fail-open or mute on the real wiring: (1) PreToolUse settings
  invoked `python`, which is not on PATH on a python3-only host, and a
  hook command that cannot start is a non-2 exit -- Claude Code continues
  the tool call. (2) Guard verdicts printed to stdout; Claude Code feeds
  stderr to the model on exit 2, so the block reason never arrived.
  (3) An exception in the dispatcher is exit 1, which is also continue.
  (4) A process-list crash or empty parse from check_editor_clear read as
  "clear to launch". (5) PUSH_RE matched `git stash push` and
  `git commit -m "...push..."`. (6) Session start pointed at the generated
  gitignored `.claude/skills/` surface, so a fresh checkout had no
  discoverable skills, and game-skill sync read only that generated
  surface (so an OS-shaped game working root's canonical `skills/` was
  invisible; a generated copy of the harness corpus would have been
  re-prefixed). Rule: prove a control through the exact wiring the
  consumer uses, including the interpreter name and which fd the harness
  reads; fail closed on enumerator crash; point the router at the
  canonical tree. Candidate skill target: prove-a-control,
  prove-an-instrument-can-fail, verify-on-the-real-entry.
  Fixed this session (wrapper + exec, stderr copy, exception -> 2,
  editor enumerator fail-closed, tighter PUSH_RE, worktree gitignored
  fallback that names the path, session-start sync, canonical game
  skills). Limit left open: PreToolUse only sees Claude Code
  Bash|PowerShell -- a Cursor Shell tool or a raw git push does not hit
- 2026-08-14 -- Dual-environment harness integration and guard resilience pass:
  (1) Added `AGENTS.md`, `.agents/hooks.json`, and `hook_antigravity_pretooluse.py`
  so Google Antigravity IDE / 2.0 shares identical routing and fail-closed safety
  guards with Claude Code. (2) Updated `sync_skills.py` to dual-mirror to both
  `.claude/skills/` and `.agents/skills/` with worktree `resolve_gitignored` support.
  (3) Fixed `GIT_C_RE` in `hook_pretooluse.py` to handle quoted paths containing
  spaces (`git -C "D:/path with spaces" push`). (4) Added offline fallback in
  `preflight_push.py` parsing `remote.origin.url` so `public-grant.txt` manual
  overrides work without network `gh` dependency. (5) Expanded secret patterns in
  `scrub_terms.txt` for Google AI, AWS STS, and GitHub app tokens. (6) Created
  `scripts/doctor.py` for <80ms session health diagnostics. (7) Authored 6 new
  game production skills: `inspect-and-patch-blueprint-graph`, `orchestrate-user-playtest`,
  `audit-animation-montage-pipeline`, `bridge-dcc-asset-roundtrip`,
  `pin-collision-and-trace-matrix`, `triage-engine-crash-dump`.
  All 110 tests green, strict scrub clean. `[distilled → skills and code]`
  CORRECTION 2026-08-14: "strict scrub clean" was FALSE when written and is
  still false. `SCRUB_REQUIRE_LOCAL_TERMS=1 SCRUB_REQUIRE_TOTAL_SCAN=1
  python scripts/scrub_check.py` exits 1 on 2 hits — `AGENTS.md:18` and
  `skills/harness/bridge-dcc-asset-roundtrip/SKILL.md:43`. The test count
  was right; the scrub claim was a false green sitting in the provenance
  the next distill reads. Verify a gate by running it, not by remembering
  that you ran it.


- 2026-08-14 ??A PreToolUse matcher is an ALLOWLIST OF TOOL NAMES, not a
  description of behaviour, so every new command-running tool arrives
  unguarded and silently so. Measured: the same `git -C
  C:/nonexistent-repo-xyz` push command was BLOCKED through Bash and
  EXECUTED through Monitor (git itself answered "cannot change to ..."),
  meaning both mechanized rules were bypassable by choosing a different
  tool. Fixed by adding Monitor to the matcher and by
  `tests/test_settings_matcher.py`, proven red against the exact reverted
  matcher. Still open BY DESIGN and written into settings.json: MCP tool
  calls carry no `tool_input.command`, so the dispatcher sees "" and
  allows ??installing any git- or engine-capable MCP server would make
  CLAUDE.md's push rule false.

- 2026-08-14 ??The Antigravity guard failed OPEN for 13 tool calls
  (04:42:39??4:43:35), including the second `ffc5212` landed. Cause, from
  that harness's own log: it resolves `.agents/hooks.json`'s relative
  `scripts/hook_antigravity_pretooluse.py` against `.agents/`, looked for
  `.agents/scripts/...`, got `[Errno 2]`, logged an error and let the call
  through. Fixed with a shim AT the path it looks for ??an absolute path
  would have baked this machine's username into a tracked file in a PUBLIC
  repo. Lesson: a second harness's guard needs its own liveness evidence.
  Nothing in this repo would ever have noticed; it was found only by
  reading another product's log by hand.

- 2026-08-14 ??Knowledge in the repo that never reaches the moment it
  matters is not knowledge. `GAME.local.md:33` has said "User's editor UI
  is Korean; match error strings by shape/position" for days; a session
  still wrote a matcher against English pin display names, lost an engine
  boot to it, and rediscovered the fact from a Korean error string. Same
  shape twice more the same day: `scrub_check.py` already carried the cp949
  `backslashreplace` fix and the brand-new `session_start.py` crashed on
  exactly that; and a stale `:200-212` citation was copied forward from a
  skill into a fresh evidence file without being checked. Routing is the
  bottleneck, not capture. `[??session_start.py, SessionStart hook]`

- 2026-08-14 ??Orientation that depends on the agent performing a ritual is
  a dependency on memory; replace it with a measurement that runs itself.
  `scripts/session_start.py` (~180ms, no network, always exit 0) is wired
  to the SessionStart hook and reports NOW.md freshness, the open register
  with duplicate detection, inbox counts and distill age, per-repo unpushed
  counts, guard matcher coverage, and skill-routing parity. Its first run
  found four defects nobody had noticed: a duplicated KG-DMG-1 register id,
  3 unpushed commits across the two game repos, CLAUDE.md routing 19 of 26
  skills (`triage-engine-crash-dump` unrouted while 300 crash dumps sat on
  disk), and ??via its own does-this-path-exist check ??two successive
  parser bugs of its own. A gate that catches its own author on day one is
  the kind worth keeping.

- 2026-08-14 ??The push guard matches its regex against the WHOLE command
  string, so a heredoc that merely quotes a push command is blocked as if
  it were one. It fired on an `Edit`-equivalent append whose payload was
  this very lesson file. Fail-closed, so the direction is right, and the
  cost is only a detour ??but note it before "fixing" it: narrowing the
  regex to dodge quoted text is exactly how an evasion route gets opened.
  Route around it (write the text to a file, append the file) rather than
  loosening the guard.


- 2026-08-14 ??Opening a new tool surface means auditing the guards that
  were written before it existed, not after. Both mechanized rules keyed on
  a shell string (`tool_input.command`); an MCP call carries none, so
  `command_of()` returned "" and the dispatcher allowed every MCP tool that
  could ever exist. Harmless only while zero servers were configured ??and
  the whole point of enabling Unreal's MCP was to stop that being true.
  Closed BEFORE enabling anything: a name-keyed rule blocks `mcp__*` tools
  naming a reserved act, `mcp__.*` joined the matcher, and 10 tests pin both
  the deny path and the allow path (a guard that blocked every MCP call
  would simply have been switched off). Red-first against the disabled rule.
  Order matters: install second, guard first.

- 2026-08-14 ??Two capabilities can be individually correct and mutually
  exclusive by construction. Unreal's MCP server is served BY A RUNNING
  EDITOR; `check_editor_clear` fails closed on any `UnrealEditor*` process.
  So MCP mode blocks every headless capture, probe and sweep, and headless
  mode makes every MCP tool call fail to connect. Nothing was wrong with
  either rule ??what was missing was a way to tell a deliberate editor from
  an accidental one. Without that, a headless launch fails with "editor
  process(es) running" and the obvious next move is to kill the editor,
  silently ending work someone started on purpose.
  `scripts/mcp_session.py on|off|status` declares the mode, and the guard's
  message changes while its verdict does not. Detecting a STALE declaration
  (declared, no editor) matters as much as the live one. Rule: when two
  modes cannot coexist, make the active one declarable ??a collision that
  reports itself is cheap; one that looks like a bug is not.

- 2026-08-14 — A crashed engine run's LAST LINE reads clean. Measured over
  the 2,283 `.log` files under D:/Kurogane and D:/Unreal: 211 carry a crash
  signature, and **176 of those end on `LogCore: Engine exit requested
  (reason: Win RequestExit...)`** — the same line a healthy shutdown writes.
  Zero of the 211 also contain `Log file closed`. So the tail is the one
  place the crash is invisible, and "read the last line of the log" is a
  broken instrument for exactly the case it gets reached for. Scan the body.
  Corollary for any log classifier: verify WHERE the discriminating token
  sits before choosing how much of the file to read.

- 2026-08-14 — 396 runs on this machine printed a success sentinel their own
  engine log contradicts (of 1,394 that print one at all): the script says
  `=PASS` and the log either never closed or carries a crash marker.
  `separate-execution-from-output` predicted this; the number is what it
  costs. The fix is structural, not vigilance — `run_verdict.py` reports
  EXECUTION and OUTPUT as two fields that cannot be collapsed, and carries
  `sentinel_claims_pass` as a THIRD field so a disagreement surfaces as
  `contradiction` instead of being averaged away. A sentinel is evidence
  about the script and nothing else.

- 2026-08-14 — "The artifact exists" is a weaker claim than "the run
  produced a result", and I proved it by shipping the weaker one. The FIRST
  real run through the new supervisor scored EXECUTION=COMPLETE,
  OUTPUT=PRESENT, CITABLE=yes over a report whose own first field was
  `"status": "FAIL"`. The gate checked existence and non-emptiness and
  stopped there. Added `PRESENT_BUT_FAILING`: a `.json` artifact that
  self-reports `status` in {fail, failed, failure, error, inconclusive}, or
  carries a truthy `error`, or a non-empty `errors`, is not a result.
  Deliberately narrow — `"error": null` and `"errors": []` are how healthy
  reports say nothing went wrong, and a gate that failed those would be
  switched off within a day. Rule: an output gate that never reads the
  output is an existence check wearing a gate's name.

- 2026-08-14 — A check that can only ever say "no" reads as a finding. The
  fingerprint probe asserted the RHI via the `r.RHI.Name` console variable,
  which returns `""` under UE 5.8.1 — so it reported `rhi_matches: false` on
  a perfectly healthy D3D12 run. Worse than no check: a false that looks
  measured. The authoritative source was in the log the whole time
  (`LogRHI: Using Default RHI: D3D12`). Two rules. Report UNKNOWN when the
  source is silent, never False. And assert the RHI you expected is PRESENT,
  never that `NullRHI` is ABSENT — absence of a string is also what a
  truncated log looks like.

- 2026-08-14 — My MUTATION HARNESS reported the wrong mutant's failures, and
  the mechanism is worth remembering: Python invalidates a `.pyc` by
  `(source mtime, source size)`. Two mutants written inside the same
  filesystem tick with the same file size make the interpreter reuse the
  PREVIOUS mutant's bytecode. Symptom: mutating the unparseable-JSON branch
  produced the FAILING_STATUS mutant's failure signature, and I nearly
  recorded "proven red" for a mutant that never ran. Fixes, both cheap:
  `-B` / `PYTHONDONTWRITEBYTECODE=1` plus an explicit `__pycache__` purge,
  and — the durable one — make each mutant DECLARE the test it must break,
  so "the suite went red" is never accepted in place of "the test that pins
  this mechanism went red". A red suite is not attribution.

- 2026-08-14 — That same sweep found a VACUOUS mechanism I had already
  counted as proven: disabling the truthy-`error` check broke nothing,
  because my only fixture set `status: FAIL` AND `error` together, and the
  status branch caught it first. Rule: each failure signal needs its own
  single-signal fixture. A fixture that trips two branches proves the first
  one and silently exempts the second.

- 2026-08-14 — `safe(unreal.SomeClass.some_method)` does NOT protect against
  a missing API. The attribute is resolved while building the argument list,
  so an absent method raises BEFORE the wrapper is entered. It aborted a
  fingerprint run that had already spent 152 s of editor startup, on
  `SystemLibrary.get_project_name` (which does not exist in 5.8.1). Pass the
  owner and the NAME — `call(owner, "meth", *args)` doing `getattr(owner,
  meth, None)` — and record `ABSENT` distinctly from `ERROR`. This project
  already learned this once for GroomComponent probes; the lesson existed
  and did not reach the new script.

- 2026-08-14 — A hung run and a slow run are not distinguishable by one
  timer. A wall clock alone kills legitimate long work or waits out a hang;
  a log-stall detector alone never stops a process that stays chatty
  forever. `engine_run.supervise()` runs both and records WHICH fired, so
  `KILLED_STALL` and `KILLED_TIMEOUT` stay separate verdicts. Measured
  default: stall 300 s, wall 1800 s — a real capture on this machine sat
  quiet for 14 s mid-run while shaders compiled, so a tight stall budget
  would have killed a healthy run. Also kill the process TREE: Unreal spawns
  ShaderCompileWorkers, and orphans left behind read as a phantom "editor
  already running" on the next launch.

- 2026-08-14 — When two capabilities are mutually exclusive by construction,
  give them ONE entry point that routes, not two that collide. `engine_run.py`
  refuses a headless launch while MCP is declared and names the exact
  transition; `mcp-check` reports the three independent preconditions (mode
  declared / editor running / listener on the port) separately, because "MCP
  is broken" is not a diagnosis and the three have three different fixes.
  The refusal has to name the way back, or the obvious next move is to
  destroy the other mode.

- 2026-08-14 — An open TCP port proves a LISTENER, not a PROTOCOL. My first
  `mcp-check` connected a socket to 127.0.0.1:8000 and reported "MCP is
  reachable". It would have said the same for any process that happened to
  bind that port. Replaced with a real `initialize` handshake, which is what
  finally made the claim measured: protocol `2025-06-18`, session id
  returned, `tools/list` answering. Rule: when a check's whole job is "is
  X up", make it perform X's own smallest real transaction. Connectivity is
  not capability.

- 2026-08-14 — The same diagnostic printed a FALSE STATEMENT for a while:
  it folded "mode declared" into readiness, so with the editor up and the
  server answering it announced "MCP is NOT reachable; tool calls will fail
  to connect" — when they would have succeeded. Declaring the mode is
  bookkeeping that protects the NEXT session from killing a deliberate
  editor; it has nothing to do with whether calls connect. Rule: a
  diagnostic that mixes bookkeeping into a capability verdict teaches people
  to ignore it. Report preconditions separately and only aggregate the ones
  that actually gate the thing.

- 2026-08-14 — `.mcp.json` is read at CLIENT STARTUP. Enabling an MCP server
  mid-session configures nothing usable: the session that turned it on
  cannot call it, and `ToolSearch` for the new tools returns nothing. That
  is not a broken server — the handshake succeeded from a plain Python
  process at the same moment. Wrote `scripts/mcp_client.py` so the harness
  is never blocked on a restart it cannot perform. Rule: before concluding a
  newly-enabled integration is broken, check whether the CLIENT ever loaded
  it, from outside the client.

- 2026-08-14 — Unreal's MCP `inputSchema.required` is a LOWER BOUND, not a
  contract. `CaptureViewport` advertises zero required params and its own
  description calls `captureTransform` optional ("If unset, uses the
  viewport's current camera"); calling with `{}` fails with `input param
  "captureTransform" needs a default value`, and supplying only that fails
  identically on `annotations`. Every parameter is effectively mandatory.
  Also: images come back JSON-WRAPPED IN A TEXT BLOCK
  (`{"returnValue":{"mimeType":...,"data":<base64>}}`), not as an MCP
  `image` content block, so a client handling only `type == "image"` reports
  "no image payload" for a call that fully succeeded. Read a remote schema
  as a hypothesis and confirm it by calling.

- 2026-08-14 — Walked straight into the `/Game/` path trap that
  `render-a-headless-capture` already documents. Passing
  `/Game/Kurogane/Characters/...` to an MCP tool through the Bash tool got
  MSYS-rewritten to `C:/Program Files/Git/Game/Kurogane/...`, and the editor
  answered "Asset not found" — a content-shaped error for a shell-layer
  cause. `MSYS_NO_PATHCONV=1` fixed all four calls. The skill named this
  exact failure and I still hit it, which says the warning needs to sit
  where the command is COMPOSED, not only in a skill body. Any engine-path
  argument crossing a POSIX shell on Windows needs the guard.

- 2026-08-14 — MCP's real payoff over headless, measured: a `CaptureAssetImage`
  thumbnail of `MIC_Kurogane_Skin_Head` came back in about a second and
  showed a flat grey sphere — KG-SKIN-1 confirmed visually, no basecolor
  bound. The equivalent headless proof costs a ~152 s editor boot per look.
  The two modes are not redundant: headless is for reproducible, sidecar'd,
  citable runs; MCP is for cheap iterative LOOKING at a live editor. Choose
  by whether the answer needs to be re-derivable later or just needs to be
  seen now.

- 2026-08-15 — DISTINCTNESS IS NOT SUFFICIENCY, and I proved it by defeating
  my own brand-new gate within the hour. After a sweep produced seven
  BYTE-IDENTICAL files that scored CITABLE, I added a `PRESENT_BUT_IDENTICAL`
  output state to `run_verdict.py` — a hash-group check over declared
  artifacts. The very next run passed it: seven REAL PNGs with seven distinct
  sha256s. They were seven photographs of sky with an unlit head in profile,
  mean RGB varying by under 0.5/255 across the entire sweep. Dither and TAA
  jitter make frames differ in bytes while carrying no signal at all. An
  identity test is the weakest possible form of a difference test; the gate
  has to be on MAGNITUDE against a measured noise floor, which is what
  `establish-a-noise-floor` already says and what I re-derived the hard way.
  Keep the identity check — it caught a real failure — but never read
  "the outputs differ" as "the run varied something".

- 2026-08-15 — A WHOLE-FRAME MEAN IS NOT A SUBJECT MEASUREMENT. I gated a
  character-tone sweep on the mean RGB of the render target while the subject
  occupied ~10% of the frame and sky owned the rest. A grade that moved the
  face substantially would have moved that number by roughly a unit, i.e.
  indistinguishable from noise by construction. Before trusting an aggregate,
  ask what fraction of it the thing you care about actually contributes.

- 2026-08-15 — MUTATION TESTING FOUND A VACUOUS GUARD IN CODE I HAD JUST
  WRITTEN. `identical_groups()` opened with `if len(artifacts) < 2: return []`
  and deleting it broke no test, because the `len(g) > 1` filter downstream
  already returns nothing for a lone artifact. I deleted the guard rather than
  writing a test to prop it up: a branch that cannot fail is not a safeguard,
  it is a second place for the rule to drift from the first. Run mutations
  against NEW code, not only inherited code — the reflex is to assume the
  thing you just wrote is load-bearing.

- 2026-08-15 — I BUILT A CAPTURE RIG THE PROJECT ALREADY HAD, and it cost six
  engine launches. The skill I had loaded named the entry point in its first
  paragraph (`probe_blades_mount_v1.py`, never the harness beneath it) and
  listed `KUROGANE_FACE_TONE=1` in its canonical launch block. I wrote four
  bespoke sweep scripts anyway, rediscovering framing, lighting, exposure
  lock and tick-driven capture one failed run at a time — all of which the
  proven rig had already solved and calibrated against a reference sheet.
  Rule: before building an instrument, grep the proven one for the axis you
  want to vary. If it is already an env var, the work is a launch block, not
  a script.

- 2026-08-15 — SIX RUNS OF "the tone knobs do nothing" WERE ONE ARGUMENT-ORDER
  BUG, and the user found it from a contact sheet in one glance while four
  scripted gates missed it. UE's PYTHON Rotator is (ROLL, PITCH, YAW); C++'s
  FRotator is (Pitch, Yaw, Roll). `unreal.Rotator(0.0, 180.0, 0.0)` written
  meaning yaw=180 sets PITCH=180 -- the camera photographs the subject upside
  down. Verified in-engine rather than argued: `Rotator(1,2,3)` reports
  roll=1, pitch=2, yaw=3. The same slip turned a four-YAW sweep into four
  PITCHES, rotating the head clean out of frame at 90 and 270, which is why
  three of four returned byte-identical empty sky.
  TWO DURABLE RULES:
  (1) AIM CAMERAS WITH `MathLibrary.find_look_at_rotation(location, target)`,
      never a hand-written Rotator. That is exactly what the proven rig does
      (`capture_metahuman_candidate.py:925`) and is why 144 of its runs are
      correctly framed while my hand-built rig was inverted from run one.
      Its `Rotator(-32.0, 125.0, 0.0)` LIGHT angles are not a counterexample:
      they were tuned by looking at pixels, so the numbers are calibrated
      whatever the fields are named.
  (2) Use KEYWORD args -- `Rotator(roll=, pitch=, yaw=)` -- everywhere else.
      Correct under either convention, and unreadable-wrong under neither.
  Meta-lesson, the expensive one: my gates all asked "did the bytes change".
  Not one asked "is the subject in frame, the right way up, and lit". A human
  glance answered in one second what four automated checks could not, because
  they were testing the pipeline and the defect was in the picture.
- 2026-08-16 — PIPING ANSWERS INTO A `prompts`-BASED NODE CLI MASHES THEM ALL
  INTO THE FIRST FIELD. The Ableton extension creator read piped stdin as raw
  keystrokes: four newline-separated answers concatenated into one garbled
  "Extension name", then the process died on an unsettled top-level await
  with exit 0 and nothing created. The working route: a 12-line driver that
  imports the same `prompts` module, calls `prompts.inject([...])` with the
  answers in prompt order (conditional type:null prompts consume nothing),
  sets `process.argv`, then dynamic-imports the real bin script — the REAL
  code path runs, zero reimplementation. Generally: when a scaffolder is
  interactive-only, look for the prompt library's injection hook before
  reimplementing the scaffold or bothering the user with a terminal detour.
