# Review and decisions for the Roblox team

Use the smallest review that can catch the consequences of the change.
This adapts governance-os to the existing production roles, saved-place workflow
and separate game repository. The [adoption record](governance-os-adoption.md)
identifies the inspected revision, adaptations and omitted mechanisms.

## Choose review by behavior

Classify before substantial delegation. Diff size is not risk. Record the
reason in the task or handoff; a JSON label cannot classify it for you.
Ordinary work needs no extra packet.

| Class | Roblox examples | Sufficient review |
|---|---|---|
| `ordinary-local` | Wording, investigation, reversible documentation or local cleanup without meaningful behavior changes | Inspect the exact diff and run the relevant focused check. |
| `material-behavior` | Movement, match flow, bots, HUD interaction, navigation, respawn or client/server integration | Focused behavior checks and a non-author review of the exact candidate. Include the saved place and ordinary-entry evidence for integration claims. |
| `high-risk-control` | Server validation, purchase/ownership gates, persistence, build source mappings, executable composition or harness authorization controls | Material review plus explicit bypass/failure analysis and relevant negative controls. |

Publication, uploads, account changes, purchases, paid providers, destructive
replacement and Git outward actions are separate effects. Existing user
authority determines whether they may run. A GO supplies evidence, not
permission. Complete authorized local preparation before an owner action.

Use an available independent reviewer or collaboration subagent; do not invent
a different model family or launch another provider to satisfy this method.
Reviewer labels are coordination records, not authenticated identities.

## Tie review to actual bytes

The discovery inventory answers where files are. A candidate snapshot answers
which exact files a particular review covers.

1. Finish the intended changes and relevant checks. Have the integrator identify
   affected inputs and dependencies. For game integration/release include actual
   source inputs, manifest/config, saved place and build receipt.
2. Copy the [scope template](../templates/ROBLOX-REVIEW-SCOPE.template.json)
   into a fresh local task file and replace its placeholders. `inputs` contains
   files or bounded directories; `evidence` contains actual reports, captures or
   receipts. Paths are relative to `harness` (this repository) or `game` (the
   current bound project).
3. Capture the candidate. Outputs must be new `*.local.json` files inside this
   repository, outside the selected files/directories.

   ```powershell
   python scripts/roblox_review.py capture --scope team/scope-N.local.json --out team/candidate-N.local.json
   python scripts/roblox_review.py check --snapshot team/candidate-N.local.json
   ```

4. The non-author reviewer checks actual scope, diff, evidence and relevant
   behavior. They return GO, NITS or FAIL with findings and checks actually
   performed. Use the [review template](../templates/ROBLOX-REVIEW.template.json).
   Fill `snapshotSha256` with SHA256 of the saved candidate JSON bytes;
   `Get-FileHash team/candidate-N.local.json -Algorithm SHA256` supplies it.
   Each review evidence entry names an individual file captured as evidence.
   Record command/ordinary entry, observed result and limitations in `findings`
   and the referenced evidence. A report's existence alone is insufficient.
5. Save the review to a fresh local filename and validate the explicit pair:

   ```powershell
   python scripts/roblox_review.py check --snapshot team/candidate-N.local.json --review team/review-N.local.json
   ```

6. Put current candidate/review paths in the task/handoff. If source, build,
   binding or evidence changes, inspect the delta and create a new candidate
   and review. Preserve old records.

Directory selections include all files beneath them and detect added or removed
members. Choose bounded directories such as `src`, not the whole project.
Prefer exact saved-build/evidence files; selecting a growing evidence folder
will invalidate the candidate when another result is added. The tool checks
selected scope; it cannot discover an omitted dependency.

Checks hash files without executing game code. Capture repeats the scan to
detect concurrent changes, but does not freeze another process or create an
atomic filesystem snapshot. Coordinate stable handback and recheck immediately
before relying on the record.

## What a green check establishes

Without `--review`, success means **CONTENT MATCH**: recorded bytes, directory
membership and binding still match. With `--review`, the checker also checks
the exact snapshot digest, a different reviewer label, GO/NITS verdict,
nonempty findings and captured evidence references. High-risk reviews need an
abuse analysis. FAIL, stale inputs and malformed records return failure.

This validates the supplied pair only. It is not a release admission service,
identity attestation, test runner, Studio lock or Git hook. A local account
can edit both records. Review content and the real reviewer response remain
necessary. Hashing a failing test report does not make the test pass.
Source, saved-build, runtime, multiplayer, device, user and published-service
cells in the handoff retain their own verdicts, including NOT RUN.

A FAIL stays open until the owner records remediation and the reviewer accepts
it. A GO for different scope does not close it. Name the previous candidate/
review and resolution in the task/handoff when replacing a review. The checker
does not search other reviews or implement supersession; the integrator must
reconcile those records explicitly.

## Coordination and durable decisions

For substantial delegated work, state focus as outcome, exact writable paths,
dependencies and handback condition. Keep one owner per shared file and one
operator per Studio instance in existing task contracts and team/NOW.md.

Sent, delivered, acknowledged and substantively answered are different facts.
A message receipt does not establish agreement or completed work. Read the
response and artifact before integration. Continue independent work while
waiting; do not silently take ownership of a busy worker's files.

Use existing collaboration tools. Sidebar messages still require user
authorization; this method grants no new messaging authority.
Keep only decisions that still shape the team in
[team/DECISIONS.md](../team/DECISIONS.md), with rationale and revisit condition.
The game's own NOW remains with its integration owner.
