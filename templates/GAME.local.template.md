# GAME.local — active game binding (machine-local, never committed)

Copy to `GAME.local.md` at the repo root, fill every field, and keep it
current. The router reads this before any work; guards read the roots.

## Identity

- Game name: <name>
- Short slug (used for skill mirroring as `game-<slug>-*`): <slug>

## Roots

- Working root (scripts, docs, skills, evidence — a git repo): <path>
- Project root (engine project: content, saved, experiments): <path>
- Engine root: <path>
- Working-root remote: <git remote URL, and PRIVATE/PUBLIC as verified>

## Orientation files (must exist; create from templates if missing)

- NOW.md: <path into working root>
- Lessons inbox: <path into working root>
- Live-state guide / index, if any: <paths>

## Standing authorization grants (mirror of what the user actually granted)

- Read: <roots covered>
- Headless engine launch: <yes/no, which binary>
- Write without asking: <paths covered>
- git add/commit without asking: <repos covered>

Everything not listed above is per-act: push, merge, canonical content
writes, DCC tools, paid tools, deletions, publishing.

## Machine facts that change behavior

- OS / shell quirks worth loading: <notes or "none">
- Known instrument limits (what cannot run on this machine): <notes>
