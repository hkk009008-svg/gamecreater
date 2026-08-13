---
name: edit-vendor-data-headlessly
description: Edit vendor assets, data tables, and engine config without an editor UI and without corrupting what you cannot see. Covers byte backups first, the no-op round-trip gate that catches corruption before it lands, enum pins that bind by value not name, config arrays that silently replace, and discovering real property names by harvest instead of guessing. Use before modifying any vendor asset, data table, or engine config file.
---

# Edit Vendor Data Headlessly

This skill grants no canonical-content write authority; every vendor-asset
save is separately authorized.

## When

You are about to modify a marketplace asset, a data table, or an engine
config file through scripts instead of the editor UI. Vendor data is
hostile territory: you did not author it, its conventions are undocumented,
and the write paths silently normalize, null, or reorder what they do not
understand. Every trap below shipped a corruption or wasted cycles in one
project before the countermeasure existed.

## Byte backup before anything, one level out

Copy the asset's file bytes to a directory outside the content tree before
the first write. In-engine duplicates are a second copy in the same
failure domain (`back-up-before-a-destructive-write`); vendor assets add a
reason of their own — reinstalling the pack restores the vendor's version,
not your edited one, so the backup is also the record of what you changed.

## The no-op round-trip gate, before any real write

Export the data, rebuild it without any edit, and compare against the
original. **Refuse to write until the identity rebuild is equivalent.**
This one gate caught three distinct corruption traps in a single data-table
pipeline, each of which would have silently shipped:

1. **Unregistered names null out.** Gameplay tags absent from the
   project's registry export fine and re-import as empty. Register every
   name the data uses (config file) before the round trip can pass.
2. **Display names do not import.** Enum cells exported as display text
   re-imported as the wrong values. Numeric values import correctly — so
   calibrate empirically: write probe rows per value, read back the
   display, build the display→number map per field. Never assume the
   declaration order.
3. **Unanchored field patterns shadow prefixed fields.** A regex for
   `Field=` also matches `Override Field=`. Anchor on the preceding
   delimiter.

Equivalence must be serialization-invariant (parse and compare, or
normalize before diffing), and the comparison must print its first
difference — a bare "not equal" on a 36-row table is undebuggable.

## Config arrays silently replace without `+`

Engine config (UE `.ini`) array keys repeated WITHOUT a `+` prefix replace
each other — only the last line survives, no warning. Measured cost: a
surface-name list written bare registered only its final entry, which
broke a vendor Blueprint's pins, which cascaded through an equipment
manager into the player pawn spawning as its parent's naked default — a
symptom three subsystems away from the config file. After any config edit,
re-verify the *consumers* of that config, not the file.

## A pack's Config travels with its Content

A marketplace pack migrated content-only strands every gameplay tag it
references: 161+ unregistered tags fired a once-per-session ensure and
silently no-oped every MatchesTag — attribute rows blank, item actions
dead — for a week before diagnosis (2026-08-13). Log harvesting cannot
converge: runtime-only references never appear in load warnings, and the
next one surfaces only after the previous batch registers. The byte sweep
converges in one pass — extract family-prefixed strings from all pack
asset bytes, with known-present tags as sweep controls — but filter
Blueprint-graph artifacts (`K2Node_*`, `_C'` class refs, prose after
"Family. ") or junk enters the registry. Register into YOUR config file:
it survives a pack reinstall, unlike the vendor bytes.

## Enum-keyed pins bind by VALUE, not display name

Select/switch nodes over config-registered enums store the enum **value**
per pin; display names are cosmetic. Measured: registering the right
names at wrong slots left compile errors; registering the exact slots the
asset referenced cleared them regardless of names. Recover the vendor's
original value layout from the asset's own bytes (below) instead of
guessing — the name table lists exactly which enum entries the graph
references.

## Discover real names by harvest + battery, never by guessing

Scripting-surface property names on vendor objects do not match display
labels, and reflection listings hide dynamic members. Two cycles were lost
guessing; one cycle of this found everything:

1. **Harvest** candidate strings from the asset file's bytes (printable
   runs from the name table).
2. **Battery-test** each candidate against a live object
   (`get_editor_property` per name, catching failures).
3. Trust only readback. Some real names carry trailing spaces; some
   structs print as `{}` while their members read fine through generated
   member names — verify by reading a member back, never by repr.

## Editor-session state lies about assets

- Creating an asset at a path where one was deleted earlier in the same
  session fails; reuse-or-edit instead of delete-recreate.
- Asset saves are blocked during play-in-editor; sequence saves after the
  session ends.
- Property writes on some sub-objects report success and do not persist
  through save/load — verify persistence with a cold reload
  (`verify-on-the-real-entry`), and prefer the engine's factory/API route
  over direct property surgery when one exists.

## Vendor content and version control

Vendor bytes never enter the repo (license), which means edited vendor
assets are **unversioned by construction**. The byte backup plus a written
record of the exact edit (what changed, from what, verified how) is the
only recovery path — keep both in the game's versioned tree, and say in
the record that a pack reinstall reverts the edit.

## Evidence rules

Record per edit: the asset path, backup path and hash, the no-op gate
result, the exact rows/fields changed with before/after values, the
consumer verified afterwards, and the cold-reload result. An edit whose
no-op gate was skipped is unaudited even if nothing visibly broke.

Related: `back-up-before-a-destructive-write` for the backup discipline;
`verify-on-the-real-entry` for why the consumer check runs cold;
`prove-a-control` for making the round-trip gate fail on purpose once.

## Provenance

One combat-wiring arc (2026-08-11/12): the tag-nulling, enum-reset, and
regex-shadowing traps all caught by the round-trip gate before landing;
the bare config array that cascaded into a replaced player body; the
enum-value pin discovery that cleared a vendor Blueprint's last compile
errors headlessly; two cycles lost to guessed names.

## Changelog

- 2026-08-12 — Authored from the combat-wiring arc's inbox entries.
- 2026-08-13 — Config-travels-with-Content section. Forced by: the Hyper
  pack's stranded tag registry (161 log-harvested + runtime-only refs
  found by asset-byte sweep; game inbox entry of 2026-08-13).
