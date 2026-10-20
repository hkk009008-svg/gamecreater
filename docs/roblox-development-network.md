# Development Mapping department

This department answers four practical questions: who owns each piece, what it
depends on, which production step it is at, and which evidence still blocks the
claimed result. It serves the game integrator, implementation workers and QA.
One person can perform this function; a department does not require another
permanent chat or a fixed team size.

The reusable engine is [roblox_development_map.py](../scripts/roblox_development_map.py).
It checks an explicitly authored graph, traces declared relations, compares
dated snapshots and writes a new local report. The analyst supplies meaning
from actual source, task contracts and evidence. The tool does not infer source
semantics, dispatch work, determine authority or run a game.

Use this map to understand a task and its evidence, not to replace its contract,
current owner or build adapter. It is derived from Game's actual production loop,
including a candidate whose source, saved build and local match flow passed while
rendered UI failed. Volatile progress belongs in a dated local snapshot.

## Intake and responsibility

Use this department when the user asks for order, progress or a relation map;
when a substantial task spans several owners or prerequisites; or when a failed
stage sends a candidate back through a correction. A small, clear edit can use
the existing task record alone. Refresh only affected relations when evidence
changes; an idle chat needs no repeated audit.

Start with the [mapping intake](../templates/ROBLOX-DEVELOPMENT-MAP.template.md).
Read the router, binding, owner-maintained task/NOW and prior snapshot before
following evidence links. Take a compact chat snapshot only when authorized and
needed; inspect new saved evidence after a meaningful change. Record a cutoff,
exact candidate, excluded scope, allowed writes and questions to answer.

| Department responsibility | Handoff and boundary |
|---|---|
| Observe | Read actual assignments, interfaces, failures and saved results; keep current owners' state read-only |
| Model | Separate scope, people, production, runtime and evidence views; name each relation and its supporting references |
| Check | Reject malformed references and ambiguous graph structure; optionally compare declared evidence hashes with current files |
| Explain | Return a navigable map, ordered handoff description and open evidence cells with owners |
| Learn | Propose a reusable mechanism from demonstrated cases; send a bounded patch request through the owning workflow |

The integrator retains task order, shared interfaces, implementation and final
handoff. QA retains independent review. This department can identify a dependency
or stale record without changing either owner's files. It reports routing
uncertainty rather than silently rebinding a project or messaging a new owner.

## Engine input, actions and output

**Input:** a dated schema-version-1 JSON graph with route/task/candidate identity,
nodes, typed edges, view membership, evidence references and limits. Each node
records owner, reads, output, declared status and the basis of its claim. Keep
source observations, assignments, prescribed methods, reviewed evidence and
proposed or pending work distinct. Every edge names a relation kind and supporting
evidence IDs. An edge may explicitly inherit its endpoints' references; these
identify supporting locations for analyst review, not proof of the relation.
The [fictional JSON example](../templates/ROBLOX-DEVELOPMENT-MAP.example.json)
shows the minimal shape. Replace its placeholders before operational use;
structural validity cannot establish that a claim is true.
Before a saved candidate exists, keep its `id` and `sha256` as `null` and its
final verdict as `UNKNOWN` or `NOT RUN`. Do not invent an identity to map planned
work. Evidence reference hashes remain explicit declarations of inspected bytes;
the fictional example's reference is a placeholder and must be replaced.

**Actions:**

For a runnable schema example from a fresh checkout:

```powershell
python scripts/roblox_development_map.py check --map templates/ROBLOX-DEVELOPMENT-MAP.example.json
```

That example is fictional and establishes no game evidence. With an authored
local graph, use the task's actual path and node IDs, for example:

```powershell
python scripts/roblox_development_map.py check --map team/game-development-network-20261021.local.json
python scripts/roblox_development_map.py trace --map team/game-development-network-20261021.local.json --node g_visual --direction out --depth 2
python scripts/roblox_development_map.py compare --before team/map-before.local.json --after team/map-after.local.json
python scripts/roblox_development_map.py report --map team/game-development-network-20261021.local.json --out team/development-maps/leaf-b-observed-001.md
```

`check` checks structure without reading referenced evidence. Add
`--verify-evidence` to read and compare the named local files. A changed file is
reported as drift; the tool never replaces its recorded digest. Sequential reads
cannot freeze an active integration or authenticate a claim. `trace` follows
recorded arrow direction, with optional kind filtering; adjacency is not proof
of impact, permission or a runnable schedule. `compare` shows explicit data
changes and does not transfer old passes to a new candidate.

**Output:** structured JSON check/trace/difference results, or a new Markdown
report under ignored `team/development-maps/`. Reports include view diagrams,
owners, input/output descriptions, references and limits. Existing output is
never overwritten. Original reports and failed candidates remain in their
owner's evidence store. Use the existing candidate-review tool for a substantial
engine change, and the visual workbench for actual image/motion evidence.

This is an offline mapping engine. Automatic source extraction, live scheduling,
cross-chat dispatch and a unified build runner remain separate proposals.

## Department operating sequence

1. **Locate the truth.** Identify the game, host/chat, task owner, exact candidate
   and evidence cutoff. Record conflicting or stale text with its newer source.
2. **Choose the question and views.** Map only the relevant scope levels, owners,
   production handoffs, runtime interfaces and independent evidence stages.
3. **Read and connect.** Inspect actual supporting material. Assign stable node
   IDs and explicit arrow meanings; record unknowns without filling them by guess.
4. **Check the model.** Run structure checks, inspect traces and optionally verify
   evidence identity. Review substantive relations against the actual source.
5. **Explain the next boundary.** Show the current result and owner of each open
   condition. A proposed next step remains a proposal until its authority exists.
6. **Retain the observation.** Save a new dated snapshot/report, compare with the
   last useful snapshot and extract only demonstrated reusable mechanisms.

Do not compute a completion percentage from node counts or numbered stages.
Production can branch, run concurrently and return to an earlier step. A
`depends-on` edge points from the dependent to its prerequisite; other relation
kinds have their own literal direction and are not scheduling constraints.

## Keep three dimensions separate

| Dimension | What it answers | Typical values |
|---|---|---|
| Scope level | What contains or owns this piece of work? | Harness → bound game → task/leaf → assigned package → exact file or artifact |
| Production step | What is done next, and what does it produce? | Baseline → contract → parallel work → integrate/review → save → exercise → hand back |
| Evidence stage | What has actually been established for these bytes and this entry? | Source, saved build, cold entry, multiplayer, presentation/device, user, published service |

These are navigation dimensions. They are not completion percentages, Roblox
player levels or an enforced scheduler. A file may participate in several tasks
over time. A worker assignment is bounded by its current task, not by a role name.

## Scope and responsibility levels

| Level | Entity | Responsibility and boundary |
|---|---|---|
| S0 | Reusable harness | Team methods, skills, templates, checks and learning records |
| S1 | Bound game/project | Canonical source, saved places, product decisions and game evidence |
| S2 | Task or leaf | One observable outcome, dependencies, authority, acceptance and stop boundary |
| S3 | Assigned work package | One owner, exact writable files/interfaces, expected handback and checks |
| S4 | File, instance or artifact | Concrete source/input/output identity; distinguish source from saved or live state |

The human supplies task authority and subjective acceptance. Game integrates the
bound project and operates its assigned Studio. Server, presentation and build
work can run concurrently when their writes are disjoint. Non-author QA checks
stable handbacks. An observer can read evidence and improve this harness without
becoming a game writer or Studio operator. Scale the team to ready work and
integration capacity; a role-count example is not a quota.

## Production steps and handoffs

| Step | Reads | Produces | Return path |
|---|---|---|---|
| Re-baseline | Current owner/task, source, exact predecessor and receipt | Input identity, preserved bytes and discrepancies | Changed inputs invalidate affected conclusions |
| Bound | Intended result, preserved behavior, authority and dependencies | Exact file/interface/check contract | Scope conflict returns as a concrete amendment |
| Dispatch | Independent ready packages and available integration capacity | Named assignments and expected handbacks | Waiting/overlap calls for resizing or serialization |
| Implement and diagnose | Canonical assigned source, raw failures and controls | Frozen changes, relevant source checks, retained failures | Correct the owning game or instrument layer |
| Integrate and review | Worker outputs, dependencies and selected evidence | Exact combined candidate and proportional non-author verdict | Findings go back to the assigned owner |
| Save and compare | Reviewed inputs and existing build/save path | Fresh saved artifact, receipt and supported source parity | Source/build mismatch returns to its owning layer |
| Exercise | Exact saved bytes and relevant ordinary entry | Separate runtime, multiplayer, rendered/device results | A failure returns to diagnosis and bounded correction |
| Hand back | Candidate/review, stage results, cleanup and limits | Owner-maintained state and one next executable action | Honor the explicit task/next-leaf boundary |

Use only relevant steps for the change. A documentation edit does not require
Studio. A test plan, dispatch or returned file is not an accepted implementation.
Review and hashes identify selected content; neither grants an external effect.

## Evidence stages are independent cells

| Stage | Useful proof | What it does not establish |
|---|---|---|
| Source/rules | Actual-module logic, compilation, mappings and meaningful fault controls | Saved/runtime integration or appearance |
| Saved build | Named bytes, input receipt and intended serialized content | Ordinary entry or gameplay |
| Cold entry | That exact saved artifact opens and runs the relevant production entry | Untested multiplayer or devices |
| Multiplayer | Specific independent clients and scenarios | Scale, unsampled latency or all match configurations |
| Presentation/device | Qualified captures, actual layout/motion and measured device cases | User judgement or untested physical hardware |
| User | The user's recorded visual, control or feel verdict | Unperformed service/account behavior |
| Published service | Authorized release and actual account/purchase/rejoin paths | Untested users, regions or policies |

Preserve PASS, FAIL, NOT RUN, BLOCKED and USER PENDING separately. A failed final
review can coexist with narrower source/build/runtime GOs. A new correction has
its own inputs and candidate; do not copy the old candidate's passes onto it.
Staged renderer states must remain separate from naturally earned progress or
service behavior. Reach reserves, visible pixels and actual input failures are
different observations.

## Typed relations make the map useful

| Relation | Meaning | Invalid inference |
|---|---|---|
| contains / depends on | Scope or prerequisite relationship | A future dependency is already authorized |
| assigns / owns | Recorded current responsibility and exact write slice | A role grants a whole subtree or enforced lock |
| calls / publishes | Observed source or runtime interface | Source inspection proves every runtime execution |
| produces | A step emitted a named output | Output existence proves correctness |
| checks | A tool/reviewer inspected selected inputs or evidence | Review grants authority or fills missing stages |
| blocks / returns to | A failed or missing condition requires a bounded next action | The observer may perform the next owner's task |
| supersedes | An explicit newer grant/result replaces a stated earlier checkpoint | Historical failures may be deleted |
| learned from | A demonstrated case informs a reusable method | The proposed adapter has been implemented |

Keep graph nodes distinct for the task, the saved candidate, its evidence and a
later correction. In particular, an approved correction is not an accepted new
build, and a final FAIL does not erase useful narrower results on the old build.

## Runtime relationships need their actual call direction

A progression example illustrates the difference between ownership and calls:
match callbacks emit ledger results; the profile service applies XP rules and its
store/schema boundary, then publishes a private owner snapshot. A client adapter
delivers that snapshot to profile and result presentation. Game state separately
controls participant/phase visibility and movement-control layout.

Do not infer direct module calls from adjacent concepts. Read the actual source:
the profile service can call XP rules even when the ledger does not. A reserved
client request kind is not proof the server implements the corresponding reward.

## Retain a dated, inspectable snapshot

A useful local map records:

- Observed time, project/chat/host, task and candidate identities.
- Each node's type, scope, owner, input, output, result and result limits.
- Each edge's explicit relation and supporting source/report reference.
- Observed source, recorded assignment, prescribed method and proposed work as
  separate bases; future work remains visibly queued.
- Exact source/report hashes and a sequential-read limitation. Fingerprinting a
  file does not imply every line was inspected or that a snapshot was atomic.
- Stale wording and the explicit grant/result that supersedes it.

The dated `team/game-development-network-*.local.json` snapshots use this shape.
They are observations, not an automatic live dashboard. The companion local
report links actual evidence and records open ownership. The shared
[team guide](roblox-team.md), [workflow contracts](roblox-workflow-engines.md),
[task template](../templates/ROBLOX-TASK.template.md) and
[visual workflow](roblox-visual-quality.md) remain the operational methods.
The [mapping checkpoint](../team/development-mapping-checkpoint.md) records the
reusable delivery scope, verification and remaining proposals.
