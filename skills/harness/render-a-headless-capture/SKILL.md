---
name: render-a-headless-capture
description: Launch an engine editor headlessly and get a citable result, not an unreadable run. Covers -nullrhi killing every capture, the shell variable that makes -abslog vanish, log calls that never reach the console, exit codes that lie, and a level load that silently renders the previous world. Use before writing or launching any headless editor command line, or reading a run log for a result.
---

# Render a Headless Capture

This skill grants no launch, save, canonical-content-write, or
external-effect authority: every headless launch and log write is
separately authorized.

## When

You are about to hand-write a headless editor command line (Unreal:
`UnrealEditor-Cmd`), or read a finished run's log file and call it a result.
Both are how runs stop being citable. Build the line from one builder, and
gate on the JSON artifact the script writes — never on the exit code, never
on a log line.

```
<engine>/Binaries/Win64/UnrealEditor-Cmd.exe <abs>/Project.uproject `
  -unattended -nosplash -NoLiveCoding -notraceserver -nop4 -stdout -NoLogTimes `
  -abslog=<abs>/logs/run-01.log `
  -ExecutePythonScript=<abs>/scripts/capture.py
```

## `-nullrhi` and `-RenderOffscreen` are opposites, not variants

`-nullrhi` means no GPU, no RHI, no rendering — it is **not** a
window-suppression flag. The flag for *render, but no window* is
`-RenderOffscreen`. A scene-capture rig or a render-queue job under
`-nullrhi` cannot produce one pixel, and screenshot tests cannot work.
Refuse to *build* a command containing `-nullrhi` when the run's declared
intent needs rendering — a pre-flight refusal beats a post-hoc log scan.
And make the guard positive: assert the RHI you expected (`D3D12`, `Metal`)
is present, not merely that `NullRHI` is absent — absence of a string is
also what a truncated log looks like.

## A shell variable in `-abslog` costs the whole run, silently

`-abslog=$log` with a shell variable can silently mangle the argument: the
editor launches, exits immediately, writes zero log bytes and zero renders,
raises nothing. The symptom reads as "the engine crashed on startup." Pass
a literal, quoted, absolute path emitted by the command builder. Put every
flag after the `.uproject` path, and build the line in one place — a
measured census of one project found 122 script-launch sites of which 11
had no `-abslog` at all (uncitable runs) and 118 were missing a flag the
canonical line carried. Hand-written command strings drift; one builder
emitting the line from declared intent (`needs_world`, `needs_rhi`,
`will_save`) fixes it by construction.

## `-ExecutePythonScript` loads a level; `-run=pythonscript` does not

Two documented routes, and the difference is whether an editor world exists:

- **`-ExecutePythonScript=<file>`** — full editor, project open, default
  startup level loaded, then your script runs.
- **`-run=pythonscript -script=<file>`** — fast commandlet, **no level
  loaded**; call the level-load API yourself. Its failure mode is the
  dangerous part: a silent no-op or a `None` return, not an exception.
  Anything touching UI, content browser, viewports, or the editor world is
  unreliable-to-absent — treat "does subsystem X work under `-run=`?" as an
  empirical question per subsystem, per engine version.

Default to `-ExecutePythonScript`; reserve `-run=` for pure-write, no-world
work where startup cost dominates.

## A silent level load renders the previous world and still reports PASS

Measured instance: a POSIX-looking `/Game/` path handed through a POSIX
shell layer on Windows was converted to `C:/Program Files/Git/Game/...`;
the level-load call fails *silently* on a bad path, the previous world
stayed current, and the run captured a character floating in an unlit void
— with `errors: []` and PASS. Three fixes, all cheap:

1. Validate the shape of every path-like input at entry, in the process
   that consumes it; name the shell-conversion trap in the error text.
2. After loading, read the world's path back and raise on mismatch — the
   load returns a bool whose `False` is silent, so never call it bare.
3. Level loads discard the current world without saving — guard anything
   the run built in memory before switching.

## The engine's log API routes most calls away from the console

In Unreal, `unreal.log()` writes at `Log` verbosity — file only, never the
console; `log_warning`/`log_error` reach both. One project measured 92% of
its logging at the invisible level, and "the milestone line went missing
from stdout" cost real debugging time. Use warning level for milestone
lines that must be visible live, and JSON for anything a gate will read.
Separately: Python's `logging` default handler writes to stderr, which the
engine tags **Error** — so `logging.info("starting")` surfaces as
`LogPython: Error: starting` and trips every "fail on ERROR" gate. Install
a handler that dispatches by record level.

## Exit codes are not a gate — the JSON artifact is

Commandlets have a history of not propagating failure exit codes, and a
crash surfaces as an access-violation code, not a clean nonzero. The result
channel is a structured artifact the script writes to a declared absolute
path. Rank the channels: the abslog for diagnosis; the script's own JSON
report for gates; stdout as a progress bar only. Exit code 0 with no
artifact at the declared path is not a pass — it is a run that died before
it had a result.

## You cannot sleep for async work — keep the script alive and tick

Shader/groom compilation, streaming, and play-in-editor are asynchronous,
and `time.sleep()` blocks the thread that would do the work. The editor
also closes on the next tick after the script returns unless told
otherwise:

```python
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
cb = unreal.register_slate_post_tick_callback(tick_fn)
...
unreal.unregister_slate_post_tick_callback(cb)
unreal.EditorPythonScripting.set_keep_python_script_alive(False)
```

**A run whose readiness predicate never went true reports INCONCLUSIVE, not
PASS.** The first run after a content change is a throwaway while caches
warm — warm once, discard, then measure.

## The failures here arrive as a silent `None`, so assert at the call site

The scripting layer prefers returning `None`/`False` to raising, so the
failure arrives as a no-op downstream of its cause. Assert every
`load_asset`, subsystem getter, and world getter non-None at the call site;
wrap every bool-returning editor call in an assert. Route them through one
compat module so the assertion (and the next API deprecation) is one file
edit, not hundreds.

## Name the failure from the log's shape, not from the exit code

| What you see | What it is |
|---|---|
| Editor launches and exits in seconds; no log, no renders | mangled `-abslog` argument — use a literal quoted path |
| PASS on frames of an unlit void | silent level-load failure; the previous world rendered |
| PASS on near-black frames (mean luminance ~1) | the map's only light is tick-driven and never ticked; count light actors |
| Capture files absent, log silent about rendering | `-nullrhi` on the command line — no RHI to capture from |
| Milestone lines missing from stdout, present in the log file | logged at file-only verbosity |
| `Error:` on informational lines | Python logging → stderr → engine tags stderr as Error |
| Large negative exit code | an access violation — a crash, not a script failure |
| Exit 0, no JSON artifact | the script died before writing its report; the run has no result |
| Subsystem returns `None` under `-run=` | no editor world — the commandlet does not load levels |
| Editor exits before async work lands | keep-alive was never set |

## Evidence rules

Log one environment fingerprint per run at warning verbosity: engine
version, RHI name, world non-null, required plugins enabled. A run whose
fingerprint is missing is not a failed run, it is an uninterpretable one —
discard it and say so. Record beside the artifact: the complete command
line as executed, the log path, the loaded world path read back, the RHI,
the capture size, the exit code, and the report's hash. A run whose loaded
world was not read back proves nothing about what it rendered.

Related: `establish-a-noise-floor` for reading a delta once images exist;
`separate-execution-from-output` for why a run's own PASS cannot see
whether the lights were on; `write-a-run-sidecar` for the parameters an
artifact must state to be comparable.

## Provenance

Every row of the failure table is a measured instance from one
character-project corpus (2026-07/08): the unlit-void PASS, the mangled
abslog, the 92% invisible logging, the tick-driven sun that never ticked.
Generalized 2026-08-12 from that project's full-detail original, which
remains in its game repo.

## Changelog

- 2026-08-12 — Initial generalized port; project counts kept as measured
  instances, engine specifics marked as Unreal-flavored examples of the
  pattern.
