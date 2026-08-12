# gamecreater

An operating system for building games with Claude over months, not
sessions. It exists because long-horizon work fails in characteristic ways:
sessions start blind, lessons die in scrollback or gitignored notes, the
same mistake gets paid for twice, and "verified" claims turn out to have
been verified on the wrong path. Everything here is a countermeasure with a
named failure behind it.

## What's inside

- **`CLAUDE.md`** — the session router: load order, skills by firing
  moment, the authorization boundary, the checkpoint ritual.
- **`memory/`** — the memory spine: doctrine, templates for `NOW.md` /
  the open register / arc briefs, and the lessons inbox.
- **`skills/`** — canonical skill bodies in three tiers: `method/`
  (reasoning discipline), `harness/` (engine-and-pipeline procedure),
  `lifecycle/` (the improvement loop itself). Each names the failure that
  paid for it and carries a changelog.
- **`.claude/skills/`** — the generated discovery surface (run
  `scripts/sync_skills.py`; don't edit by hand).
- **`scripts/`** — guards and plumbing: push preflight, editor-clear
  check, skill sync, publishability scrub.
- **`.claude/settings.json`** — hooks that make the two most expensive
  rules mechanical instead of remembered.

## Adopting it for a game

1. Clone this repo; open your Claude sessions anchored here.
2. Copy `templates/GAME.local.template.md` to `GAME.local.md` (gitignored)
   and fill in your machine's paths: working root, project root, engine,
   and the standing authorization grants.
3. Create `NOW.md` and a lessons inbox in your game's working root from
   `memory/NOW.template.md` and the inbox pattern in `memory/LESSONS.md`.
4. Run `python scripts/sync_skills.py` to build the skill surface,
   including your game's own skills as `game-<name>-*`.
5. Work. Append lessons as they happen; distill them into skills at arc
   ends; keep `NOW.md` true at every checkpoint.

## Principles

- **Memory is layered by lifetime.** Standing corrections outlive
  projects; current truth lives one place and is updated at checkpoints;
  lessons are captured raw immediately and distilled deliberately later.
- **Only mechanize what failed.** A guard exists because its rule was
  broken expensively, not because it might be. Everything else stays
  advisory, so the system doesn't calcify.
- **A gate proves nothing unless it runs the real path.** The single most
  expensive class of failure this system encodes.
