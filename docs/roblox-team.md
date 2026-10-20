# Roblox game-making team

This repository coordinates Roblox production. The active game and its local
paths come from `GAME.local.md`; the game's `NOW.md` records current product
truth. Keep reusable workflow here and implementation, builds and game evidence
under the bound game root. An old prototype contract is historical context
until its interfaces and scope have been checked against current source.

The production pattern behind this guide comes from the working Roblox project:
bounded source changes, focused actual-module checks, a timestamped saved place
bound to its inputs, then fresh Studio entry with runtime readback and captures.
Keep concrete script names, commands, results and their evidence in the local
project dossier linked from team state. Adapt that demonstrated path to the
next task; this guide does not prescribe a replacement build system or require
every acceptance stage for every edit.

## Start a session

Read `AGENTS.md`, `GAME.local.md`, `team/NOW.md` and the bound game's `NOW.md`.
Check skill mirrors as directed by the router. Confirm the current task, its
implementation owner and existing edits before assigning work. The team's
coordination state must not replace or silently rewrite game state.

When another chat already owns a release pass, review it or contribute an
explicitly assigned slice. A new coordinating chat does not take over the same
source files. Follow the user's active exclusions recorded in the local binding
and team state; removing a game from scope grants no file-deletion authority.

## Roles and file ownership

Use the roles needed for the task. One person or agent can cover several roles;
a small change does not require five running agents.

| Role | Responsibilities | Ownership boundary |
|---|---|---|
| Lead and integrator | Scope, dependencies, shared interfaces/config, assembly, build, task board and final handoff | Assign exact writable paths; retain one owner for shared config, build scripts and current-state files. |
| Server gameplay | Match state, combat rules, matchmaking/bots, persistence and entitlements | Own assigned server files. Server validates client intentions and controls authoritative outcomes. |
| Client and presentation | Input, HUD, camera, animations, effects and responsive layouts | Own assigned client files. Request shared-interface changes through the integrator. |
| World, art and audio | Map builders, local asset preparation, lighting and sound presentation | Own named world/presentation files. External asset insertion, generation, upload and purchases depend on their actual authorization. |
| QA and release | Relevant regression checks, saved-build playtests, evidence review and publishing handoff | Review implementation read-only unless assigned a distinct fix. Return reproducible failures to the file owner. |

Role names do not grant blanket ownership of a directory. Use
[`ROBLOX-TASK.template.md`](../templates/ROBLOX-TASK.template.md) for substantial
delegated work. Record exact writable files or bounded instance paths, shared
interfaces, preserved behavior, acceptance target and evidence destination.
Read-only investigations can run alongside writers. Two writers must not edit
the same file concurrently, even if they intend to change different functions.

If new scope requires another owner's file, agree on a handover or have that
owner perform the edit. Never revert, format or stage unrelated work as part of
an assigned slice. The integrator reviews each delivery before the combined
build; a worker's green result does not establish integration success.

Use subagents for bounded parallel tasks. Creating a separate user-owned chat
and sending messages to another chat follow the product's tools and the user's
authorization. A team role does not authorize paid providers or external agents.

## Source, saved place and Studio

Record the project's source-of-truth model before editing:

- **Source-built project:** local Luau and builder inputs are canonical. Make
  durable changes there, then generate a new saved place. Studio patches are
  experiments until reproduced from those inputs.
- **Studio-native project:** the named Edit document is canonical. Back up the
  saved place before replacement, save deliberately, and verify by reopening
  its saved bytes. Do not introduce a source synchronizer as an unrelated task.

Avoid unsynchronized dual ownership between disk and Studio. A Play-time change
does not become a durable fix merely because the current session behaves well.
Keep temporary probes and fixtures identifiable and remove them from the test
session before the final ordinary-entry check.

One named operator owns mutations for a Studio instance: Edit changes, starting
or stopping Play, input injection, camera/simulator changes and fixture cleanup.
Other agents can inspect agreed state read-only or work on independent files.
Record the operator, intended file/place, operation and handback condition in
team/task state. This is a coordination record; claim an enforced lock only if
a real mechanism has been implemented and exercised.

Before Studio work, list connected instances and identify the intended target
from its current name/file/place. Query its current state and available data
models. Use a current `studio_id` and an appropriate Edit, Client or Server
target on tools that require one. Re-list after reconnection, replacement or
resumption; historical receipts do not establish today's instance or mode.
Do not start, stop or take over the user's active play session without their
instruction. A hold stops mutations and input immediately.

Inspect currently available tool schemas instead of inventing APIs or assuming
a tool name supplies permission. Retrieve Roblox tool skills when relevant:
documentation search for uncertain APIs, device simulator for layout checks,
profiling/scene analysis for performance investigations, debugging for runtime
failures, and unit-test guidance for actual unit-test work.

Treat execution context as part of evidence. An MCP `require` may not share the
same VM/cache as an ordinary production LocalScript. Observe the running
instances or use a scoped ordinary script when that distinction matters.
Batch expensive execution with bounded chunks and yields; an unyielding script
can freeze Studio. A successful input call establishes submission only: observe
focus, pause state and the resulting player action before claiming behavior.

## Acceptance and evidence

Apply [proportional review](roblox-governance.md) to substantial behavior and
control changes. A non-author reviews the explicit candidate; the local
candidate checker detects changes to selected inputs/evidence. Ordinary local
edits need no formal packet. Review and the stage results below remain separate.

Choose checks proportional to the change. A label edit needs a saved/rendered
check in the relevant layout; a combat, queue or purchase change needs the
appropriate runtime and negative cases. Stop broadening tests once relevant
checks pass unless new changes, failures or unresolved concerns justify more.

| Stage | Evidence it can provide | What remains separate |
|---|---|---|
| Source and rules | Compilation, mappings, actual-module logic, malformed-request rejection and focused regressions | Runtime integration, appearance, player feel and devices |
| Saved build | New named place, exact inputs/receipt and intended serialized source or content | Cold loading and ordinary gameplay |
| Cold ordinary entry | Reopen that saved place; lobby, Practice/match, fresh spawn, respawn and return through production paths | Multiplayer, physical devices and subjective acceptance |
| Multiplayer | Actual independent clients exercise authority, team flow, disconnects and shared mechanics | Scale, latency conditions or devices that were not exercised |
| Presentation and devices | Captures/motion, UI measurement, profiling, specific emulated and physical-device runs | Unsampled hardware, comfort and user judgement |
| User acceptance | The user's observed verdict on appearance, controls, pace or feel | Unperformed service/account checks |
| Published service | Authorized released version and actual account/ownership/purchase/rejoin paths | Unperformed users, regions, platforms or policy qualifications |

Use `PASS`, `FAIL`, `NOT RUN`, `BLOCKED` or `USER PENDING` per relevant stage.
Do not collapse them into a single completion label. Record setup, expected
behavior, observed result and evidence. Name fresh/warm state, saved build,
entry flow, client/server context and any test doubles or disabled layers that
limit the conclusion. A test cannot pass from an empty selector, an absent
subject, an artifact's mere existence or a tool's success wrapper.

For a release candidate, bind results to an exact saved file and input receipt;
use a hash when available. Preserve predecessors and failed evidence. If source
changes after a check, recheck the affected behavior on the resulting saved
build. Fixtures that manufacture retired modes or stations cannot establish
integration with the actual lobby.

For human playtests, supply the exact build/entry, at most three actions and
observable expected signals. Ask at most two distinct gameplay questions per
round. Record the user's verdict as given. Simulator layouts, screenshots and
automated rules do not close physical-device or feel acceptance.

## Release and publishing handoff

Use [`ROBLOX-HANDOFF.template.md`](../templates/ROBLOX-HANDOFF.template.md) for a
release or durable hold. Update the team's coordination state and have the
game owner update the game's `NOW.md`; do not create competing current truths.
Record unsaved or live-only state as an explicit blocker. Commit only where
authorized and applicable; do not initialize a game repository merely to make
a checkpoint ritual fit.

The publishing portion must name:

1. The exact saved build, input receipt, known issues and predecessor/rollback.
2. Intended account or group, verified Universe ID and Place ID, and which
   owner actions remain. Preserve missing IDs as missing.
3. Asset/pass/product mappings, permissions, sales flags and entitlement rules.
   Distinguish confirmed ownership/equipping from eligibility to buy. Account
   test doubles must remain separate from actual purchases and rejoining.
4. The activation sequence: configure owner-managed resources, return verified
   IDs, integrate and check mappings, produce the activation build, publish the
   exact authorized version, enable sales as intended, then run live checks.
5. Published purchase, cancellation/failure, ownership restoration and rejoin
   checks relevant to the feature. Never make a charge merely to fill a cell
   without the user's authority for that purchase.
6. Any optional private-server setup, audio/image upload, permissions or other
   resource setup still requiring the account owner.

At execution time verify current official Roblox documentation for relevant
publication, pass, server, reward and account requirements. Do not encode
changing rates, payout forecasts, eligibility thresholds or tool capabilities
as permanent policy in this guide. Cite the specific official source and date
when a release decision depends on it.

Local preparation and review can proceed within existing authority. Publishing,
uploads, spending, account changes, destructive replacement and Git push/merge
use the exact grants in the local binding and user instructions. Complete the
concrete reviewable work before a remaining approval step; a release plan does
not itself grant that external action.
