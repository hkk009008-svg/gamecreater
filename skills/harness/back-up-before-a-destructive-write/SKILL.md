---
name: back-up-before-a-destructive-write
description: Make a backup that provably exists before a script deletes, duplicates, overwrites, or re-imports an asset. Covers the phantom backup whose log line was true and whose directory was empty, the existence predicate that lies in both directions, delete-then-create holes, and inverted dry-run polarity. Use before arming any apply gate or writing the first destructive call.
---

# Back Up Before a Destructive Write

This skill grants no gate-arming, canonical-content write, delete, commit,
or push authority. Each is a separate act needing its own authorization.

## When

You are about to run a script that deletes, duplicates, overwrites, or
re-imports an asset, and you have written a backup step you have never
watched fail. **The backup step is the part that fails.** Four scripts in
the originating corpus logged a backup path, returned success, and left
nothing on disk; the edits they guarded were irreversible at the moment
their logs said they were safe. Prove the bytes are on the filesystem
before the destructive call, or do not make the call.

## Every failure in this family logs success

All six symptoms produce a green run and exit 0. None raises.

| What you see | What it is |
|---|---|
| Backup path printed, run green | in-engine duplicate with no save — a live object, not a file |
| Existence predicate true, no file on disk | registry membership, not a file |
| Duplicate into an existing path returns `None` | the file was removed behind the engine; the registry still lists it |
| Second run in one editor session skips the save | the "already exists" short-circuit reading its own phantom |
| Original gone, replacement absent | delete-then-create where the create failed |
| A bare invocation with nothing set wrote content | inverted or misplaced dry-run gate |

## A logged backup path is not a backup

In-engine duplicate calls hand back a truthy live object that dies at
editor exit unless a save runs. Measured instance: the backup directory
**did not exist at all** while four scripts' logs claimed backups there;
one overwrite was recoverable only because an unrelated export happened to
be on disk. Luck closed that incident, not the guard.

## An existence predicate over a registry is not a predicate over a file

Demonstrated on a throwaway asset: the engine's exists-check returns true
for an unsaved in-memory duplicate AND for a path whose file was deleted
behind the engine — it lies in both directions, which is why "backup
already there" and "backup just written" read the same. The proof sequence
that works:

```python
saved    = save_asset(backup_path)          # read the return value
sys_path = resolve_to_system_path(backup)   # engine → real filesystem path
require(os.path.isfile(sys_path), "backup absent")   # ask the filesystem
```

Keep a third state, `checked=False`, so "no file" and "could not look" are
different answers. And run one damage→restore cycle on a scratch asset as
the positive control: without a restore that lands on the exact pre-damage
number, "no raise" is indistinguishable from a probe that never touched the
asset.

## Never short-circuit on "already exists"; reuse, never overwrite

`if not exists(BACKUP):` around the backup sequence means a second run in
the same editor session sees the in-memory phantom, skips the save, and the
trailing re-check is satisfied by the same phantom. This recurred across
four hardening passes in three days — one script carried a comment
describing the exact failure directly above code still committing it. A
destructive script's second run must never clobber the pre-first-run state.

## Delete-then-create leaves a hole, and the cleanup path is the same trap

Delete-then-create where the create can fail destroys the original and
produces no replacement. Build the replacement first; swap only once it
exists. Cleanup runs in a `finally`, or it runs only when nothing went
wrong — the case that never needed it.

## Default-deny, and gate the operation, not just the save

Two measured gates made destruction the default: one dry-run variable with
**inverted polarity** (unset = commit), and one commit flag tested outside
its enclosing condition so a bare invocation committed anyway. The house
shape: report-only by default; one env flag `<PROJECT>_<THING>_APPLY=1`
defaulting off; durable backup before the write; a `require()` on the
number that would embarrass the run. Gate the whole operation at the top,
never one limb of it. And put the gate + backup + require helpers in ONE
imported module — polarity defects become a one-file fix instead of an
N-script sweep.

## Parsing is not running, and your interpreter is not the engine's

Dozens of scripts were "verified" by parsing with the system Python; the
engine embeds an older one. A construct legal in the newer parser raised
SyntaxError in-engine. Re-verify with the binary that will run the code
(`<engine's own python> -m py_compile <file>`). Two more defects only
running can find: an API that does not exist in the engine version, and an
argument type the bindings refuse.

## A backup inside the thing that can destroy it is not a backup

An in-engine duplicate is a second copy in the same failure domain; the
next script can overwrite it. Durability starts one level out: version
control over the asset tree (large binaries through LFS), and **commit is
not push** — a commit that exists on one disk is the same incident one
level up.

## Before you say "backed up"

- [ ] The save call's return value was read, not discarded.
- [ ] The backup was confirmed by a filesystem check on a resolved system
      path, never by the engine's exists-predicate.
- [ ] "No file" and "could not look" are distinguishable in the report.
- [ ] No exists-short-circuit anywhere on the path.
- [ ] No delete-then-create: the replacement exists before the original
      goes.
- [ ] Cleanup is in a `finally`; a deliberately failed run leaves zero
      scratch assets.
- [ ] The gate wraps the whole operation, defaults to report-only, and a
      bare invocation was measured writing zero files.
- [ ] The script was compiled by the engine's own interpreter.
- [ ] A restore was actually run once and landed on the exact pre-damage
      number — a backup never restored is a hypothesis.

Related: `prove-an-instrument-can-fail` for making the guards fire on
purpose; `pin-a-content-boundary` for the version control that must exist
before any script is allowed to write.

## Provenance

The phantom-backup incident (2026-08-05), the both-directions existence
predicate, the four-pass short-circuit recurrence, and the inverted dry-run
gates are measured instances from one character-project corpus. Generalized
2026-08-12.

## Changelog

- 2026-08-12 — Initial generalized port.
