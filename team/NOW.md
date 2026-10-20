# Roblox team - current coordination

**As of:** 2026-10-20 KST.

## Current arc

The Roblox team conversion and actual-game method extraction are complete.
The follow-up researched the user's governance-os at commit
2d413f6dfea3661a0bc33300d47e1250d6968d08 and adopted proportional review,
exact candidate/evidence checks and durable decisions. The local binding selects
Strikepoint. Game implementation remains with its existing release owner.

## Active ownership

| Work | Owner | Write boundary | State |
|---|---|---|---|
| Strikepoint release, shop fixes, body/bots, 1v1/2v2 and five-map roulette | Existing Shooter chat | Game source, builds and game NOW | Await owner's current saved-build handoff |
| Harness conversion and method extraction | This conversion chat | This repository only | Complete; 383 harness tests passed |
| Independent review | Architecture reviewer | Read-only findings | Engine/config/inventory review finished |
| governance-os adaptation | This chat; delegated checker author | Harness docs, templates, review checker and tests | Complete; 403 tests run, 401 passed, 2 platform skips |
| Adoption review | Independent research/implementation and workflow reviewers | Read-only findings | GO for local adoption; no game acceptance claim |

These rows coordinate ownership; they are not cross-process locks. Do not start
a second writer or Studio operator for the existing release pass.

## Next executable action

Run `python scripts/roblox_team.py check`, then read the game's latest handoff
and receipt. If Shooter is still integrating, keep new work read-only or in
disjoint harness files until handback. Refresh the inventory when reconciling
source and saved-build state. For a new substantial change, choose review scope
with docs/roblox-governance.md and bind the candidate to its actual inputs/evidence.

## Open register

### Blocks release claims

- **GAME-HANDOFF** - Shooter owns the actual saved release and runtime results.
  Harness conversion does not establish gameplay completion.
- **PUBLISHING** - publication, pass creation/IDs, activation, purchases and
  published rejoin tests remain owner actions. Follow the game's current handoff.

### Closed team setup work

- **HARNESS-CHECKS** - 383 harness tests passed; real startup and setup checks
  ran; official new-skill validation passed; 42 skills match both mirrors.
  Receipt: [setup-validation-20261020.local.json](setup-validation-20261020.local.json).
  Game builds/runtime were not exercised by this conversion.
- **GOVERNANCE-ADOPTION** - Local regression run: 403 tests, 401 passed and two
  platform-specific skips (actual symlink privilege and FIFO availability).
  Controlled symlink/reparse-refusal tests did execute. Independent code and
  workflow reviews returned GO. Setup/mirror checks passed (42 skills).
  Evidence: [test receipt](governance-adoption-tests-20261020.local.json),
  [review findings](governance-adoption-review-findings-20261020.local.json),
  [candidate](governance-adoption-candidate-20261020.local.json) and
  [bound review](governance-adoption-review-20261020.local.json).
  This is the historical adoption pair. The publication checkpoint updates
  this state file and clarifies the router's guard description, so that earlier
  snapshot is expected to be stale. Recheck current candidate bytes before
  reuse. The checker does not enforce review history or publishing.

## Active blockers

No external account is required for local team setup. The game's final runtime
and publishing steps remain with its release owner. Its NOW may lag source;
inspect timestamps, input hashes and scope receipts.

## Scope and evidence

Iron Paws is excluded from active work and handoffs by user instruction.
Previous games and evidence are preserved. The original binding and ten pre-edit
files plus two later-touched tests are hash-preserved in the conversion backup.
Existing unrelated tracked files match their pre-edit working-tree hashes.
The user explicitly authorized committing and pushing the Roblox setup and
governance adoption on 2026-10-20. This checkpoint accompanies that scoped
commit to origin/main. Git's local/remote refs establish delivery status.
The push also carries five existing ancestor commits needed by this harness.
Unrelated working-tree edits, local bindings, generated mirrors, dossiers,
inventories, backups and detailed local evidence stay outside the new commit.
The governance follow-up's eight pre-edit files and tracked-file baseline are
under .local-backups/governance-adoption-20261020T224227156/pre-edit.
Local dossiers/inventory
describe inspected snapshots, not gameplay, user acceptance or publication.

The committed-source check is performed from an export of the exact staged
tree, separate from the mixed working directory. Its receipt is stored locally
under the publication backup; the earlier 403-test receipt describes the full
working directory, including unrelated uncommitted tests.

## Adopted operating methods

- [governance-os research and selection](../docs/governance-os-adoption.md)
- [Proportional review and exact candidate workflow](../docs/roblox-governance.md)
- [Current reusable decisions](DECISIONS.md)

## Derived project knowledge

- [System dossier](strikepoint-system.local.md): runtime architecture, modules,
  remotes, maps/modes/bots/avatar/commerce and sixteen failure-to-method records.
- [Pipeline dossier](strikepoint-pipeline.local.md): actual tool locks, backup,
  reviewed builds, serialization/readback and Studio handoff methods.
- [Inventory](inventory-20261020T133435949379Z.local.json): 14,508 files and 174
  selected workflow fingerprints in the observed game tree; no read/change errors.
  This is a non-atomic snapshot from an active integration, not current acceptance.

## Visual workbench checkpoint — 2026-10-20

The offline visual workbench is implemented and independently reviewed.
Its [checkpoint](visual-workbench-checkpoint.md) records the delivered scope,
verification and open evidence limits. Start a new authorized visual study with
`python scripts/roblox_visual_packet.py init --help`, then follow the
[workbench guide](../docs/roblox-visual-workbench.md). Game's release state and
next task remain governed by its current local binding, NOW and owner handoff.
The user authorized committing and pushing this bounded harness work; generated
packets, original game captures and other pending harness work remain separate.
