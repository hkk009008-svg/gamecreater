# governance-os adoption record

Research date: 2026-10-20 KST.

Source: [hkk009008-svg/governance-os](https://github.com/hkk009008-svg/governance-os),
default branch `main`, inspected commit
[`2d413f6dfea3661a0bc33300d47e1250d6968d08`](https://github.com/hkk009008-svg/governance-os/tree/2d413f6dfea3661a0bc33300d47e1250d6968d08).
The GitHub description still says "four-seat"; inspected code and docs name
three desktop members. This adoption follows the inspected code.

Research read README, AGENTS, ARCHITECTURE, OPERATIONS, DECISIONS, risk classes,
review composition/validation, admission, status, team transport, preflight,
hidden bindings and relevant tests. Upstream tests were inspected, not executed.
No upstream provider, hook, installer or desktop service was run. The source
checkout and pre-edit backups remain in the ignored
`.local-backups/governance-adoption-20261020T224227156/`.

## Adopted and adapted

| Mechanism and inspected source | Why it helps | Local implementation |
|---|---|---|
| Proportional review: `docs/protocol/agents/risk-classes.md`, `pipeline/codex_protocol_model.py:ReviewProfile` | Keeps small work direct; scrutinizes behavior and trust changes | `docs/roblox-governance.md`; risk/reason and reviewer fields in task/handoff |
| Exact candidate binding: `pipeline/review_flow.py:publish_request`, `accept_request`; `compact_pair_loop.py:parse_verify_request` | Stops an earlier review silently covering changed source | `scripts/roblox_review.py` captures selected inputs/evidence; review binds the saved snapshot digest |
| Fresh content validation: `pipeline/status.py:_review_state_key` | Size/mtime alone can miss edits | Fresh SHA256 reads, including selected saved places/evidence; no status cache |
| Preserve evidence: `pipeline/ci_admission_gate.py:_artifact_changes`, `compact_pair_loop.py:_supersedes_violations` | Keeps failed and replaced results reconstructable | Exclusive-create snapshots, fresh review filenames and explicit remediation/supersession in handoff; no automatic ledger |
| Review never grants effects: `ARCHITECTURE.md`, `DECISIONS.md:D6` | A reviewed shop fix cannot authorize a purchase or publication | Existing authorization boundaries retained |
| Observational focus/handoff: `pipeline/team_messages.py:status`, `pipeline/team_mcp.py` | Clear ownership and handback reduce duplicate edits | Existing contracts/team NOW; delivery is distinct from an actual reply |
| Durable rationale: `DECISIONS.md:D7` | Avoids rediscovering why source and integration ownership are separate | `team/DECISIONS.md` keeps current reusable decisions |

An upstream gap influenced this adaptation:
`pipeline/compact_pair_loop.py:_require_path_references_resolve` explicitly
does not verify bare SHA256 evidence references (lines 408-411 at this revision);
`tests/unit/test_compact_pair_loop.py` documents that behavior.
Our checker opens and hashes evidence files and requires review references
to resolve to captured evidence. It cannot prove the reported command ran
or the evidence supports a conclusion.

The local helper is a new standard-library implementation of these methods,
not an installation or copy of the upstream service.

## Deliberately omitted

| Upstream mechanism | Reason |
|---|---|
| Three-member app bindings, model allowlists and prescribed reviewer families | Available collaboration workers fit this team. Labels cannot attest a running model; a provider mandate adds an unrelated dependency. Non-author review and abuse analysis transfer cleanly. |
| Git request/report auto-commits and merge choreography | The current game folder is not a Git worktree; this task grants no commits or merges. Source/build bytes provide a useful binding. |
| SQLite mailbox, new MCP server and app plugin registration | Existing tools deliver work. Importing hidden bindings would replace integrations and messaging boundaries. |
| POSIX store protections and `/usr/bin/git` assumptions | The transport relies on Unix ownership, permissions and locking. This workspace uses Windows. |
| CI authority admission from trusted base and historical supersession graph | Useful for a future Git release pipeline, but absent from a local pair checker. No CI/hook enforcement claim. |
| A packet for every ordinary edit | Adds work without improving small wording changes or investigations. |
| No standing integrator | Shared Roblox manifests/config, saved builds and Studio state need explicit ownership. Existing functional roles remain. |

## Validation and limits

Local regressions exercise content/evidence changes, directory membership,
binding drift, malformed/empty records, wrong candidate digest, self-review
labels, FAIL, missing high-risk analysis, output containment and preservation.
Deliberately failing fixtures must fail; a successful fixture must pass.
The local run receipt and independent reviewer findings are linked from team/NOW.md.

This adoption does not test or modify the game, attest reviewer identity,
configure desktop integrations, enforce ownership locks, authorize external
effects or establish release readiness. Revisit the omitted admission/transport
features after a demonstrated coordination failure or adoption of a Git-backed
game release pipeline.
