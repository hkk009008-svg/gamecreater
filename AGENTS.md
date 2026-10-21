# gamecreater - Roblox game-making team

This repository runs a Roblox production team. Game source, saved places and
evidence live in the separate project named by GAME.local.md. Keep this repo
for reusable methods, team coordination, skills, checks and handoffs.

## Core value: balanced parallel production from evidence

Use the smallest effective team. Scale concurrent work to independent ready
packages, clear file ownership and the lead's integration capacity. Keep one
integrator and one Studio operator; merge evidence and changes deliberately.
A user's request for multiple worker chats covers creating and assigning those
chats within that approved task. Use short-lived subagents for bounded work and
separate worker chats for substantial self-contained packages when authorized.

Study actual modifications and debugging, including failed hypotheses and
broken instruments. Specialize proven steps into reusable workflow engines with
explicit inputs, actions, outputs and limits. Reuse working components before
adding machinery. The [team guide](docs/roblox-team.md) and
[engine contracts](docs/roblox-workflow-engines.md) make this value operational.
The [core workflow checkpoint](team/core-workflow-checkpoint.md) records this adoption.

Use the [Development Mapping department](docs/roblox-development-network.md)
for requested process/order maps and substantial work whose owners, dependencies
or evidence stages need clarification. Its offline engine checks dated relation
graphs, traces declared connections and compares snapshots. Keep the map
proportional to the question, refresh affected evidence after meaningful change,
and leave active game/state writes and dispatch with their existing owner.

Use the [learning workflow](docs/roblox-learning-workflow.md) at substantial task
intake and handback: retrieve relevant learning IDs, retain useful cases, choose
the smallest reusable form and record actual reuse outcomes. Development Mapping
curates its own local index; no fixed lesson quota or extra engine is required.
Keep proposed, implemented, delivered and reused status distinct, and preserve
the game's ownership and the existing arc-end skill-edit boundary.

The user has given standing authorization to notify the bound Game integration
chat after completed relevant harness instruction/workflow/behavior changes.
Use the current binding's chat/host, send the concrete change, checks, delivery
status and application to remaining work, and record receipt separately from
acknowledgement/adoption. Reuse the same change identity to avoid duplicate
notices. This does not authorize worker-chat dispatch, another leaf, Game file
edits or external effects. If routing is uncertain, report it instead of guessing.

## Start every session

1. Read GAME.local.md: engine, project roots, integration owner and exact grants.
2. Run `python scripts/sync_skills.py --check`; sync only when drift is reported.
3. Read team/NOW.md and the active game's NOW.md. Follow its latest handoff and
   build receipts; compare timestamps/hashes to source. A newest directory is not
   proof of an accepted build.
4. Read docs/roblox-team.md and use build-roblox-game for Roblox implementation,
   Studio testing and delivery. Run `python scripts/roblox_team.py status`.
5. Assign exact files and acceptance checks before delegating implementation.
   For substantial behavior/control changes, apply docs/roblox-governance.md:
   choose proportional review and bind the result to the exact candidate.

Current files and actual results outrank remembered state. If NOW is stale, record
the discrepancy and have its integration owner reconcile it. Do not overwrite
another active chat's state file while it integrates a release.

## Operate as a team

The lead owns scope, shared interfaces/config, integration, builds and handoff.
Delegate server gameplay, client/UI, world/art/audio and QA/release when independent.
Roles and task contracts live in docs/roblox-team.md and templates/ROBLOX-TASK.template.md.

- Every task has one owner and exact writable files. A role does not grant an
  entire source subtree. Resolve overlapping assignments before writing.
- One operator owns a Studio instance's mutations, Play transitions and input.
  Enumerate current Studios and inspect the chosen instance before live work.
  Studio IDs and Edit/Client/Server contexts expire; old evidence is not a target.
- Other workers can read source/review evidence and prepare disjoint changes.
  Shared config, mappings and interfaces go through the integrator.
- Use collaboration subagents for current-task work. Create or message sidebar
  chats only under user authorization. The current integration owner keeps its
  game files until an explicit handback.
- On hold, immediately stop edits, tests, launches and input. Preserve state.
  Do not interrupt or take over the user's current play session.

The initial local binding selects Strikepoint. Iron Paws is excluded from active
work, planning and handoff by the user's decision. Exclusion never means deleting
its files. Historical Unreal projects remain separate and inactive.

## Derive methods from the actual game

Inspect the active project's actual scripts, manifests, lessons and receipts.
Keep changing facts in team/*.local.md / *.local.json, not permanent generic
rules. `python scripts/roblox_team.py inventory` indexes files and fingerprints
workflow inputs without executing them. It is not proof every artifact was read.

Use the project's existing reviewed build wrapper. Preserve scope checks and
input hashes; save a fresh candidate rather than overwrite evidence. A tool call,
compile, fixture or build cannot establish gameplay, visual quality, multiplayer
fairness, physical-device behavior or user approval. Use feature-relevant stages
in docs/roblox-team.md; do not rerun every stage after every small change.

Before release handoff, cold-open the exact saved candidate and exercise ordinary
player entry. Report source, saved-build, runtime, multiplayer, visual/device,
user and published-service results separately. Use templates/ROBLOX-HANDOFF.template.md.

Use `scripts/roblox_review.py` to capture/check explicit candidate inputs and
evidence for substantial reviews. A matching snapshot proves content identity;
it does not fill missing acceptance stages or grant authority. Preserve failed
reviews and reconcile remediation explicitly. Ordinary local work needs only
focused verification. Durable team rationale lives in team/DECISIONS.md.

## Work from skills

Read the applicable skill in `skills/` or its discovery mirror before its work.
build-roblox-game is the Roblox entry.
docs/skill-routing.md routes retained general methods and legacy engine skills.
Unreal-only procedures do not apply to Roblox because they are discoverable.
Preserve originals; check both generated discovery mirrors.

## Authorization and guard limits

The user's task and exact grants in GAME.local.md govern work. Reversible local
implementation within an assigned user-requested task can proceed; setup does not
transfer another project's permissions or release ownership. This conversion
authorizes harness changes, not competing game edits.

Exact authority is required for publication, account/purchase changes, paid or
provider tools, uploads, DCC launches, push/merge, visibility changes and destroying
or overwriting existing assets/evidence. Local commit authority is separate.
Do not infer authority from a role, plan or work mode.

Hooks guard repository publication names, pushes and lesson truncation.
The Unreal CLI and shared policy helpers reject a non-Unreal binding.
These checks do not validate arbitrary Roblox Luau or
enforce the written file/Studio ownership protocol. Do not call a written rule a
mechanized lock. Codex hook trust/running state is not observable here; do not
change or bypass hooks merely to make work run.

## Persistence and handback

Append paid-for general lessons to memory/LESSONS.md; coordinate project lessons
with the game's owner. Existing skill bodies change at arc end through
distill-an-arc on the user's go. New skills requested by team setup identify their
source and limits.

Before hold or arc handback, follow checkpoint-a-hold: current team/game state,
next executable action, tiered register, exact evidence and outstanding ownership.
Commit only when authorized; report uncommitted work honestly. Push is separate.
