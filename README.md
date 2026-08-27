# gamecreater

`gamecreater` is the small control repository for long-running Unreal game
work. The game project and generated evidence live in the paths configured for
the active game; this repository keeps only the shared router, skills, guards,
and launch tools.

## Start here

- `AGENTS.md` is the authoritative workflow and authorization boundary.
- `GAME.local.md` binds this checkout to the active game, engine, project,
  working root, and standing grants. Copy `templates/GAME.local.template.md`
  when setting up a new machine.
- The active game's `NOW.md`, whose path is recorded in `GAME.local.md`, is the
  current plan, register, blockers, and next executable action.

Claude runs session orientation automatically. After a checkout or any change
to `.codex/hooks.json`, review and trust that exact definition with Codex's
`/hooks` command; a configured file is not proof that Codex is running it.
Orientation can always be run directly:

```powershell
python scripts/session_start.py
```

## Unreal entry points

Use the supervised launcher instead of constructing an Unreal command line:

```powershell
python scripts/engine_run.py mode
python scripts/engine_run.py automation "^Exact.Test.Name$"
python scripts/engine_run.py headless path\to\probe.py --artifact path\to\report.json
python scripts/engine_run.py data-validation
python scripts/engine_run.py epic-mcp-check
```

- **Live editor:** open the configured Unreal project, then use Codex's
  OpenClaw stdio bridge for inspection, PIE control, and reversible tuning.
  Canonical mutations still require the exact authorization named in
  `GAME.local.md`. An open editor intentionally blocks headless runs.
- **Automation:** run one bounded native Unreal test or prefix after a change.
  A zero-match selector is a failure, not a green empty run.
- **Headless:** close the editor first, then use `engine_run.py headless` for
  probes, captures, and sweeps.
- **Data Validation:** run the stock whole-project asset scan at checkpoints,
  not after every edit; large vendor-heavy projects can take many minutes.
- **Optional Epic HTTP MCP:** `.mcp.json` describes Epic's separate
  ModelContextProtocol HTTP surface. It is not OpenClaw and is not required for
  Codex live-editor work. `engine_run.py epic-mcp-check` only checks this optional
  endpoint.

Keep the verification ladder proportional: native Automation per change,
focused headless probes for behavior or renders, Data Validation at a
checkpoint, and UAT/Gauntlet packaged smoke only when packaging work begins.
Add no new orchestration layer until one of those native paths cannot express
the required check.

## Skills and tests

Canonical skills live in `skills/`; game-specific skills come from the active
working root. Refresh the generated discovery surfaces after skill changes:

```powershell
python scripts/sync_skills.py
```

Run the repository test suite with:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```
