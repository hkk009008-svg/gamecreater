# Debug case — <observable symptom>

Use for a diagnosis worth retaining within the existing task. Keep it short;
omit fields that do not affect this case. This record adds no approval gate.

## Identity and reproduction

- Task / owning chat / host / file owner: <current identity>
- Expected behavior and actual symptom: <one concrete difference>
- Original failure and raw log/capture: <preserved paths and hashes>
- Source / saved candidate / input receipt: <exact identity or unknown>
- Fixture, capture or report-tool identity: <separate path/hash from game source>
- Reproduction entry: <ordinary fresh entry or exact staged setup; cold/warm>
- Context: <Edit/Client/Server, clients, device, input and relevant state>
- Reproducibility: <attempts, failures, intermittency and untested conditions>
- Allowed diagnostic effects and exact writable slice: <current task reference>

## Qualify the observation

- Known-positive control: <what should be detected and actual output>
- Subject/selector: <present, unobscured, intended distance; or not applicable>
- Instrument coverage: <what this path can and cannot observe>
- Independent witness: <different read/capture mechanism when needed>
- Visual context: <camera/FOV, viewport, quality, rendering layer, native/stepped
  motion, encoding/scaling and repeat evidence when relevant>
- Race/order context: <events, yields, in-flight operations, ownership and
  expected terminal state; or not applicable>

## Discriminate causes

| Plausible cause | Read/control and predicted signal | Actual result / evidence | Disposition |
|---|---|---|---|
| <cause> | <what separates it from another cause> | <raw output> | <supported / eliminated / unexamined> |

Use a cheap direct test when one cause dominates. Batch cheap independent reads
when several causes remain plausible. Retain unexamined causes and controls
that could not observe their known-positive; silence alone does not eliminate a
cause. Preserve wrong diagnoses with their correction.

## Attribution and correction

- Attributed layer: <game logic / fixture / build-checker / capture-transport /
  platform / unresolved; evidence and limits>
- Correction: <smallest owning-layer change, or explicit need for another read>
- Source versus instrument changes: <which hashes changed and which did not>
- Why the control failed: <behavioral assertion, syntax/fixture error or unknown>
- Rollback: <preserved predecessor or not applicable>

## Replay and handback

- Original-case replay: <actual command/entry, exit status, output and artifact>
- Relevant regression/negative control: <result and exact evidence>
- Saved build and cold entry: <result or NOT RUN; no inheritance from fixtures>
- Visual/device/user acceptance: <separate scoped result, NOT RUN or USER PENDING>
- Remaining causes/limits: <specific open cells>
- Owner handback / next action: <one executable action>
- Engine candidate: <reusable mechanism, supported inputs, side effects,
  controls, failure behavior and remaining proposal; or none>

## Extraction and reuse (optional)

Use the [learning workflow](../docs/roblox-learning-workflow.md) and a local
[learning index](ROBLOX-LEARNING-INDEX.template.json) when this case yields a
reusable lesson. Preserve the original failure chronology; record later
qualification separately. No extraction quota, new tool or skill is required.
Existing guidance, a duplicate, project-only knowledge, rejection or deferral
are valid dispositions.

- Stable learning ID / local index: <ID and index path, or none with brief reason>
- Latest qualified disposition / evidence cutoff: <current supported result,
  observed-through time and supporting reference; do not rewrite earlier results>
- General mechanism / applicability / exclusions: <what transfers, when to use
  it, and conditions or effects this case does not support>
- Durable form / reason / owner / destination: <existing guidance, doc/checklist,
  test/helper, skill candidate or no promotion; why this form; owner and exact path>
- Implemented change / review / delivery: <exact change or method version,
  proportional review and delivery references; separate proposed from implemented
  and record missing or unknown evidence>
- Next reuse target: <task and candidate if known, intended entry and expected
  use; pending is valid and a planned use is not a completed reuse>
- Actual reuse receipt: <task/candidate, actual entry, method version/hash,
  adaptations, observed outcome and evidence, and remaining limits; NOT RUN
  when no reuse has been observed>
