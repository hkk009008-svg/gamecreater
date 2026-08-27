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
  probes, captures, and sweeps. CPU probes default to `-nullrhi`; use
  `--needs-rhi` for pixels. With one `--artifact` path, the child receives the
  same path as `ENGINE_RUN_ARTIFACT` and the supervisor verifies its fresh bytes.
- **Data Validation:** run the stock whole-project asset scan at checkpoints,
  not after every edit; large vendor-heavy projects can take many minutes.
- **Optional Epic HTTP MCP:** `.mcp.json` is an internal endpoint descriptor
  read by these local scripts; it does not register a Codex MCP server. It
  describes Epic's separate ModelContextProtocol HTTP surface. It is not
  OpenClaw and is not required for Codex live-editor work. `engine_run.py
  epic-mcp-check` only checks this optional endpoint.

Every real supervised launch holds one cross-process lease through verdict and
sidecar publication, so two agents cannot start Unreal together. `--dry-run`
validates the command without requiring the editor to be closed or taking that
lease.

Keep the verification ladder proportional: use one registered native Automation
selector when the changed subsystem has one; otherwise use a pure test plus one
focused probe. Use Data Validation at a checkpoint, and UAT/Gauntlet packaged
smoke only when packaging work begins.
Add no new orchestration layer until one of those native paths cannot express
the required check.

## Skills and tests

Canonical skills live in `skills/`; game-specific skills come from the active
working root. Check the generated discovery surfaces first, and rewrite them
only when drift is reported:

```powershell
python scripts/sync_skills.py --check
python scripts/sync_skills.py
```

Run the repository test suite with:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```
