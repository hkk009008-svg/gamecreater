# Development Mapping checkpoint

As of 2026-10-21 KST. This checkpoint covers the user-requested Development
Mapping department and its offline engine. The preceding harness baseline is
`c294fcd`. The user explicitly authorized committing and pushing this scope.

## Delivered behavior

- The department explains ownership, prerequisites, production steps, runtime
  relations and independent evidence stages from actual source/contracts/results.
- The router, team guide, engine contracts and decisions route suitable questions
  to this function. Its scope stays proportional; no permanent extra worker or
  repeated idle audit is required. Integration, dispatch, Studio and current
  game state remain with their existing owners.
- `scripts/roblox_development_map.py` validates authored graphs, traces directed
  relations, compares snapshots and writes fresh Markdown/Mermaid reports.
- Graphs carry claim bases, supporting references, a cutoff and explicit limits.
  Unknown candidate identity stays null. A new candidate inherits no acceptance.
- Reports are confined to new `.md` files under ignored `team/development-maps/`.
  Local production maps, reports, game identities, captures and backups are not
  part of the reusable source delivery.

Start with the [department guide](../docs/roblox-development-network.md),
[intake](../templates/ROBLOX-DEVELOPMENT-MAP.template.md) and
[fictional example](../templates/ROBLOX-DEVELOPMENT-MAP.example.json).

## Verification and evidence boundary

Implementation validation ran 16 engine tests: 15 passed and one actual-symlink
test skipped because this Windows host lacks the privilege. The deterministic
reparse-refusal control executed. The existing review helper ran 20 tests:
18 passed and two platform-specific skips. Actual graph checks, directed return
tracing, evidence drift, comparison, new reporting and overwrite refusal ran.
Independent non-author review returned GO for the exact local implementation.

Publication checks use an export of the exact selected Git index, including the
new engine/tests, templates and only this task's additions to shared documents.
This separates delivered source from the already mixed working directory.
Detailed candidate, command-output, review and delivery receipts remain local
under `team/*.local.json` and the publication backup. Git refs and the delivery
receipt establish whether the commit reached the remote.

The earlier interactive Game observation was separately checked for model
consistency and 320px/736px interaction/layout. It remains a dated local
explanation. These results do not establish game, device, user or service
acceptance. No Game source, Studio, binding or active owner state is changed by
this publication.

## Open register and next executable action

- CLOSED — department contract, default routing, intake/example, offline engine,
  focused controls and independent implementation review.
- PROPOSAL — automatic semantic extraction, live scheduling, chat dispatch and
  game execution adapters. These are not implemented by this engine.
- OWNED ELSEWHERE — the active game's integration and release acceptance.
- EXCLUDED — unrelated pending workflow/tooling/configuration/lesson changes,
  machine-local game records and generated evidence.

For a fresh checkout, run:

```powershell
python scripts/roblox_development_map.py check --map templates/ROBLOX-DEVELOPMENT-MAP.example.json
```

Then use the intake to author a new dated local map from the current task's
actual evidence. A structural pass checks the supplied declarations; it does
not authenticate them, grant authority or start another task.
