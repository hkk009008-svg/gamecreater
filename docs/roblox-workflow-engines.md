# Specialized Roblox workflow engines

This is the design contract for reusable modification, debugging, visual and
development-mapping workflows. Task contracts, candidate review and the visual workbench are
included in the committed baseline. Saved-source parity and runtime inspection
are local extractions requiring separate inclusion; confirm their availability
before using them. A unified runner and new game execution adapters are proposals;
this document does not claim they exist.
Build each specialization from actual cases, including failures and corrected
instruments. Keep game-specific source, captures, parameters and run facts in
local task/evidence records.

## Core production value

Use the smallest effective team and scale concurrency with independent ready
work and the integrator's capacity. One lead owns the combined result. Every
worker has an exact file boundary, dependencies, acceptance checks and handback.
Independent review can run alongside implementation where its inputs are stable;
shared writes and Studio transitions stay serialized under their owner. The
[team guide](roblox-team.md) defines task sizing and worker-chat coordination.

## Development mapping engine

The [Development Mapping department](roblox-development-network.md) specializes
process, order, responsibility and progress mapping as a service to the team.
Its offline [engine](../scripts/roblox_development_map.py) implements explicit
graph checking, bounded relation tracing, snapshot comparison and new local
Markdown reports. It is separate from game execution and task dispatch.

**Input:** a dated graph with route/task/candidate identity, stable node IDs,
owners, input/output descriptions, typed relations, supporting evidence and
limits. Distinguish scope, people, production, runtime and evidence views.

**Action:** read supporting source/contracts/reports, model only demonstrated
relations or labelled proposals, check references and declared types, optionally
verify current file identity, and compare affected relations with the previous
useful snapshot. The engine checks the authored model; semantic extraction and
acceptance still require reading the evidence and proportional review.

**Output:** an inspectable relation network and stage-specific results, directed
traces, explicit snapshot changes, discrepancies and the next responsible owner.
Keep old candidate results distinct from a new approved correction. Failed
visual acceptance can return to implementation while narrower source/runtime
results remain valid for the old bytes. No result grants scope or starts a leaf.

**Limits:** declared relations are not authenticated calls, proven impact or a
schedule. Sequential hashes are not an atomic snapshot. No source extraction,
chat dispatch, Studio/build operation, acceptance promotion or external effect
is performed. Use existing task, review and visual tools for those workflows.

## Modification engine contract

**Input:** an approved behavior change, current task/decision scope, exact
predecessor and input receipt, writable files, dependency/interface ownership,
preserved behavior and the relevant acceptance stages.

**Work:** recheck the baseline; preserve rollback bytes; assign independent
packages; modify the owning source; run focused actual-module and negative
checks; inspect returned changes; freeze and review the exact candidate; use the
game's reviewed build adapter; verify saved-source identity; cold-open and test
ordinary entry when the change requires it. Integrate in dependency order.

**Output:** exact changed files and hashes, preserved failures and remediation,
source/fixture results, saved candidate and receipt, separate runtime/device/user
verdicts, cleanup and an executable handoff. A worker's pass remains scoped to
its assignment until integration is tested.

Useful existing components:

| Component | Current job | Separate question |
|---|---|---|
| [Task contract](../templates/ROBLOX-TASK.template.md) | Scope, ownership and decision boundaries | The record supplies no new authority or runtime lock |
| [Candidate review](../scripts/roblox_review.py) | Hash selected inputs/evidence and check an explicit review pair | Semantic correctness and actual execution |
| Saved-source parity (`scripts/roblox_saved_parity.py`, optional local extraction) | Compare supported manifest/script mappings with saved XML | Unsupported mappings and gameplay |
| Runtime report inspector (`scripts/roblox_runtime_report.py`, optional local extraction) | Inspect supported report consistency and supplied artifact identity | Reproducing the reported behavior |
| [Visual workbench](roblox-visual-workbench.md) | Bundle original captures, comparison conditions and evidence gaps | Visual judgement and physical-device acceptance |

The next orchestration adapter should connect these existing records and invoke
only explicitly supported steps. It must retain each stage's result and limits,
refuse unsupported inputs, and leave game build/Studio operations with the
current owner. Demonstrate reduced repeated work on a bounded task before
expanding the adapter.

## Debugging engine contract

**Input:** a precise symptom with expected/actual behavior; original raw failure;
source, saved-build and fixture/instrument identities; reproduction entry and
context; current ownership and allowed effects. Use the
[debug case](../templates/ROBLOX-DEBUG-CASE.template.md) when a diagnosis needs a
retained record; omit irrelevant fields for small cases.

**Work:** reproduce through the relevant entry, qualify the subject and
instrument, write plausible causes beside discriminating reads, run the cheapest
useful controls, and retain both eliminated and unexamined causes. For races,
record event order and yield points. Attribute the evidence to game logic,
fixture, build/checker, capture/transport, platform or unresolved ownership.
Then make the smallest supported correction in the owning layer and replay the
original case plus relevant regressions through the modification workflow.

**Output:** an evidence-supported attribution or explicit uncertainty, original
and corrected source/instrument identities, controls and actual replay output,
remaining acceptance limits, and a focused patch request or delivery. An
arbitrary nonzero exit does not prove a behavioral negative control; it could
be a syntax or fixture failure. A corrected detector does not establish a game
behavior fix.

Two demonstrated instrument failures shape this contract: a fault runner failed
to recognize native assertion stack formatting while production hashes remained
unchanged, and a text-until-next-function preservation detector included a new
global in an old Python function. Language-aware boundaries are a candidate
specialization for the latter; support for Python cannot imply support for Luau.
Preserve the original failure and replay when extracting either mechanism.

## Visual debugging specialization

Start with the player's view and identify the relevant world, avatar, weapon,
GUI or effect layer. Record actual camera/FOV, viewport, quality, device, time
and input/capture mode. Qualify visible subjects, occluders, original encoding
and positive layer controls before interpreting an absence or metric.

Use an independent capture path when a control reveals a blind spot. Compare
one deliberate factor and retain unchanged repeats for small pixel claims.
Keep reconstructed motion, native motion, runtime cost and human appearance
judgement distinct. Use the visual workbench to present the original evidence;
feed diagnosis back into one scoped modification and recapture its result.

Observed cases include a screenshot path omitting BillboardGui while rendering
ScreenGui, and an unintended foreground bot occluding the distant subject.
Neither metadata correctness nor a missing image feature identified a game
source defect. The source game retained those captures with their exclusions.

## Extract the method, then specialize

The [learning workflow](roblox-learning-workflow.md) records a stable learning ID,
qualified disposition, chosen destination/owner and actual reuse receipt. Use
the debug/task template blocks and separate local index before building more
machinery. A documented or delivered component can still have reuse pending.

For each candidate engine component, retain the triggering case, exact inputs,
actions and side effects, output, failed hypotheses, controls, supported subset
and failure behavior. Reuse the existing helper where it already does that job.
Separate a proposed extraction from an implemented adapter and from verified
production use. Keep review proportional and use meaningful fault controls for
substantive tools; skill changes still follow the existing distillation method.

A dated local study at `team/workflow-engine-study-20261021.local.json` contains
actual source/report hashes and distinguishes observed work from proposals.
It is supporting local evidence, not a release gate or permanent game state.
