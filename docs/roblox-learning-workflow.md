# Learning from Roblox production

Turn useful production evidence into methods that later tasks can retrieve,
apply and improve. Use this workflow for a substantial handback, a costly
failure, a corrected diagnosis or repeated manual work. Small routine changes
can yield no new lesson. There is no extraction quota or fixed team size.

Development Mapping curates the local learning index and links evidence to
methods. Game retains its source, implementation, Studio, dispatch and active
state. QA reviews substantial claims and tools proportionally. A role or index
entry supplies no new authority. An observer writes its own assigned records.

## The loop

1. **Observe a meaningful change.** Use current routing and prior observation
   state. Follow new handbacks, grants, failures or saved evidence relevant to
   the question. Unchanged or idle work does not require another audit.
2. **Retain the case.** Use the [debug case](../templates/ROBLOX-DEBUG-CASE.template.md)
   for reproduction, original evidence, baseline, competing causes, controls,
   correction and replay. Keep failed hypotheses and distinguish game defects
   from fixture, build, capture, transport and platform defects.
3. **Extract the mechanism.** State what transfers, its trigger, assumptions,
   supported subset and exclusions. Deduplicate against existing methods before
   choosing a durable form. Keep product-specific values and permissions local.
4. **Make a bounded change.** Name its owner and exact destination. Apply the
   existing [review method](roblox-governance.md) to substantive changes and use
   focused checks. Record proposed, implemented, reviewed and delivered status
   separately; none implies successful production reuse.
5. **Retrieve at intake.** For a substantial new task, inspect only relevant
   index entries and their current supporting evidence. Record selected IDs,
   applicability, expected use and exclusions in the
   [task contract](../templates/ROBLOX-TASK.template.md). None is a valid selection.
6. **Close the reuse loop.** At handback, record applied, adapted, not-used or
   unresolved, with the actual task/candidate, entry, method version, outcome,
   evidence and limits. A planned use remains pending until it happens.

Do not force a fixed number of cases before improving a method. One controlled
failure can justify a guard or regression. A broader engine needs a stable
recurring mechanism, explicit input/action/output contracts and meaningful
failure controls. Reuse an existing component before adding machinery.

## Choose the smallest durable form

| Learning | Destination | Boundary |
|---|---|---|
| Product choice, temporary fact or one game's setting | Game decision/state record, maintained by its owner | Observers do not edit it or turn it into a generic rule |
| Useful question or procedural reminder | Existing guide or template | Describe its trigger; avoid adding every case to the router |
| Deterministic failure condition | Focused regression or checker | Demonstrate a known-positive and the relevant failure |
| Recurring mechanical sequence | Existing helper, or bounded new tool/engine | Preserve unsupported-input behavior and per-stage limits |
| Repeatable judgment procedure | Existing skill or proposed new skill | Use the existing arc-end distillation method and applicable user go |
| Durable ownership/authority principle | Team guide, decisions and router | A written rule is not a lock or permission grant |
| Already-covered, duplicate, unsupported or low-value claim | Existing-guidance, duplicate, deferred or rejected disposition | Record the reason rather than creating an asset |

Existing skill bodies remain governed by
[distill-an-arc](../skills/lifecycle/distill-an-arc/SKILL.md): collect during work,
triage at the arc boundary, apply skill edits on the user's go. This workflow
adds no approval step to local documentation, records or fixes already covered
by the task's authority. It does not authorize Game or external effects.

## A compact local index

Start from the [index template](../templates/ROBLOX-LEARNING-INDEX.template.json)
and create a new ignored `team/learning-index.local.json`. Replace the fictional
entry and set `example` to false before operational use. The index is curated
JSON, not a database, automatic detector or enforced admission gate. This
workflow introduces no new production validator or scheduler.

Each entry carries:

- A stable ID, title and retrieval tags. IDs remain stable when a diagnosis or
  disposition changes; a different mechanism gets its own ID.
- A primary case reference and supporting evidence IDs. The evidence index
  records path, observed bytes/hash, read time and what was actually inspected.
- The latest qualified summary, its observation time and unresolved evidence.
  An old OPEN heading and a later fixture correction can coexist in the raw
  case; summarize their scopes explicitly instead of calling the whole case done.
- The mechanism, applicability and exclusions.
- The selected disposition, reason, owner and destination, plus exact change,
  review and delivery references or explicit unknowns. A local file or clause
  may exist without being committed or delivered.
- A reuse state, related observations, first actual use receipt or null, and
  the next trigger. A later similar case does not prove a guideline caused an
  improvement. Keep related evidence separate from measured reuse.

Disposition values are `existing-guidance`, `doc-template`, `regression-check`,
`helper-engine`, `skill-candidate`, `project-only`, `duplicate`, `deferred` and
`rejected`. Reuse values are `pending`, `observed` and `not-applicable`.
An observed reuse needs an actual receipt; pending use leaves `firstUse` null.
Hashes, labels and statuses remain declarations unless separately checked.

Retain a dated copy before changing the index's latest summaries. Preserve the
original cases, failed reports and earlier index snapshots. Compare referenced
bytes before relying on an entry. Changed evidence calls for qualification of
the affected claim; never silently replace hashes to make it look current.
An absent index is advisory: use the relevant existing guide and record the
missing index, rather than blocking a small task or inventing learning evidence.

## What counts as a reuse receipt

Record the actual task and candidate identity when one exists; the actual entry
or command; method version/hash; changes needed; outcome; evidence references;
and what was not measured. For a docs-only or pre-build task, candidate identity
can remain unknown with a reason. Keep source, fixture, saved-build, runtime,
visual/device, user and service results separate.

Useful observations include repeated steps removed, a failure caught before a
build, an adaptation that exposed an assumption, or the same failure recurring.
Record time savings or defect reduction only when measured. Passing assertions,
number of notes, graph reach and delivery status are not measures of learning
benefit. An unhelpful method can be revised, deferred or retired with a reason;
preserve its prior evidence.

## Reuse across team handoffs

Record reuse at the role, artifact and stage where it happened. A worker can
apply a method to analysis, preserve it in a proposed instrument, or correctly
leave it to another lane while production and runtime checks remain pending.
Keep the original worker handoff intact; append later consumer results instead
of rewriting an earlier pending statement as a whole-task success.

Use optional `reuse.events` for these short receipts. Each event names the task
and role, producer and intended consumer, exact artifact/version, stage, actual
application or reason for non-use, result/evidence, and the next owner/check.
State whether an independent analysis used shared inputs or independently
acquired evidence. Record measured and inferred inputs separately. Neither a
second analysis of the same capture nor a delivered file supplies a fresh
runtime observation.

`firstUse` points to the earliest supported application and names its stage;
it can be an analytical reuse with implementation still pending. An instrument
proposal that merely preserves correlation does not prove a fresh-response
control ran. Keep such planned execution pending even when its handoff is useful.
Do not infer time savings or defect reduction from a completed handoff.

Accept stable artifacts separately when their dependencies permit it: for
example, an integrator can consume a frozen source hash while its author finishes
a disjoint fixture. Record what was received and checked, what is still pending,
and who owns the next action. Worker completion, consumer acceptance and final
task acceptance are separate facts; this adds no mandatory ledger or review round.
If the handoff names a prerequisite check, record its actual result before
claiming that prerequisite cleared. Dispatching a reviewer or receiving a file
while review is in progress is a separate event.

## Connect it to Development Mapping

Use the existing [mapping engine](roblox-development-network.md) when a relation
view helps. Represent a case and method as artifact nodes, support as evidence
nodes, and a task/outcome as their relevant kinds. Use `learned-from`, `supports`,
`produces` and `checks` with literal directions and supporting references.
Keep observed, prescribed and proposed bases distinct. A snapshot can show
case → method → destination → next use without claiming the next use occurred.
There is no automatic index-to-graph adapter or semantic source extraction.

## Notify Game of completed changes

The user explicitly directed this repo to keep Game updated with new instructions
and behavior. This is standing authority to send the named Game integration chat
a handoff after completed relevant harness changes. It covers the integrator in
the current binding, not arbitrary chats or direct worker assignments.

1. Finish the concrete change and proportionate checks/review. Resolve the
   binding's actual chat/host; report routing uncertainty instead of guessing.
2. Send a compact handoff naming changed instructions/files and their version
   or hashes, actual checks, local versus committed/pushed delivery, and how
   remaining authorized work should use it. Preserve current scope and stop
   points; do not restart a completed check without an affected reason.
3. Record the tool receipt and change identity in a separate ignored
   `team/game-workflow-notifications.local.json`. Consolidate related completed
   changes and avoid re-sending an unchanged identity. Delivery is not agreement.
4. Check an available compact response at a safe boundary. Keep acknowledgement
   and demonstrated adoption separate from message submission; unresolved status
   remains pending. Do not claim Game changed its behavior without evidence.

This instruction supplies no Game file/Studio/state authority, no permission to
start the next leaf and no publication, purchase or Git grant. An observer keeps
other worker chats read-only. Existing automation schedules and notification
preferences remain as configured; changing this workflow does not resume a
paused observer. User-facing observation updates still follow the requested
meaningful-change policy.

## Pilot and handback

The first local pilot indexes response freshness and same-state UI sampling
from retained Game cases. Their raw history and remaining acceptance limits
stay intact. Related later evidence is useful, while prospective reuse stays
pending until a task actually records it. The
[checkpoint](../team/learning-workflow-checkpoint.md) records the implementation
and local verification. Subsequent work should demonstrate retrieval and reuse
before expanding the workflow or building another engine.
