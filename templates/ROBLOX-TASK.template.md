# Roblox team task — <short outcome>

## Assignment

- Task ID: <stable local identifier>
- Game and bound root: <from GAME.local.md>
- Requested behavior: <observable player or production outcome>
- Owner: <one implementation owner>
- Integrator: <combined build/current-state owner>
- State: <ready / working / review / blocked / delivered>
- Dependency or active release owner: <task, chat or none>
- User direction and exclusions: <current decisions relevant to this slice>
- Review class and reason: <ordinary-local / material-behavior / high-risk-control; changed behavior>
- Independent reviewer for substantial changes: <non-author; or not needed for ordinary-local>

## Learning retrieval (optional)

Use the [learning workflow](../docs/roblox-learning-workflow.md) to retrieve only
lessons relevant to this slice. The local
[learning index](ROBLOX-LEARNING-INDEX.template.json) points to evidence; it does
not grant authority or require a new tool, skill or extraction.

- Selected learning IDs: <IDs, or none with a brief reason>
- Applicability / expected use: <why each selected method fits this task and
  which entry, check or decision it should help; relevant exclusions>
- Retrieval owner / local index: <task owner and exact index path, or unavailable>

## Scope and ownership

- Source-of-truth model: <source-built or Studio-native; canonical path>
- Exact writable files or bounded Edit instance paths: <allowlist>
- Read-only dependencies: <paths/interfaces>
- Shared config/interface changes: <integrator-owned change or none>
- Preserved behavior/content: <specific invariants>
- Out of scope: <scope likely to collide or expand>
- Existing edits/other owners checked: <current observations>
- Authority needed beyond existing grants: <exact effect/target or none>

When approvals differ across steps, record this short decision scope instead of
letting a broad feature approval imply permission for its activation:

- Decision source: <direct user instruction or linked reaffirmation; quote only
  the relevant wording, record the date/chat if known, leave missing identity unknown>
- Allowed in this slice: <exact effects, executor and target already authorized>
- Deferred or forbidden now: <remaining effect and the condition or explicit
  decision needed before it can run; an approval for later is not execution now>

The record describes existing authority; it does not grant or authenticate it.

## Work and coordination

<Brief implementation approach; identify dependency order and work that can run
independently. Do not prescribe an unverified API.>

- Studio operator, if needed: <owner or not needed>
- Intended saved file/place: <path or verified identity>
- Current Studio ID and mode: <freshly observed or not yet inspected>
- Data model/context: <Edit / Client / Server as applicable>
- Mutation/input scope and handback condition: <bounded operation>
- Temporary fixtures and cleanup: <what is introduced and how removed>
- Backup/rollback for replacement: <verified location or not applicable>

Ownership records coordinate people/agents. They do not establish an enforced
lock or grant permission to take over a live user session.

## Acceptance plan

Select only relevant checks. Keep source logic, saved-build integration,
multiplayer, visual, emulated-device, physical-device and user verdicts distinct.

| Check / entry | Expected behavior | Required evidence | Owner |
|---|---|---|---|
| <actual source/module check> | <result> | <report> | <owner> |
| <cold saved-place ordinary path> | <result> | <capture/log/readback> | <owner> |
| <negative or lifecycle case when relevant> | <rejection/recovery> | <report> | <owner> |

- User/device/service acceptance still needed: <specific cells or none>
- Evidence destination: <fresh task/run directory; preserve existing evidence>
- Stop/revise condition: <failure that invalidates this plan or requires handover>
- Bypass/failure analysis for high-risk-control: <specific trust/gate cases and negative controls>
- Candidate/review records: <explicit paths from scripts/roblox_review.py workflow, or not needed>
- Prior failed/superseded review and resolution: <paths and accepted remediation, or none>

## Delivery

Return the changed-path list, behavior, relevant results/limits, exact saved
build and receipt if produced, cleanup/Studio state, open issues and next
executable action. Request shared-file changes from their owner. Do not edit
another owner's files, publish, upload, spend or push because the task exists.

### Reuse closeout

When learning was selected or discovered, keep the result brief and link the
actual evidence. Otherwise record none; do not manufacture a lesson.

- Learning IDs / disposition: <applied / adapted / not used / unresolved, with
  a reason; distinguish intended use from what actually happened>
- Actual result / evidence / limits: <task/candidate and entry, method version,
  adaptations, observed result and report path; unmeasured benefit stays unknown>
- New candidate learning: <ID/local case and next owner/action, or none>
