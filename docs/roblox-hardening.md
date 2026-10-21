# Repository hardening

Phase 1 strengthens the existing local authorization controls. It covers guard
startup, the declared shell-tool routes, repository visibility/identity checks
and the Antigravity shim's response protocol. The controls remain a bounded
check on named operations. Human authority and file/Studio ownership still come
from the task and binding; a preflight ALLOW supplies neither.

## Phase 1 contracts

| Boundary | Input and action | Result and limit |
|---|---|---|
| Configured Claude/Codex PreToolUse command | Start an isolated Python interpreter, find the repository root, load that root's `scripts/guard_entry.py` and call its `main`. Claude can use an explicit absolute `CLAUDE_PROJECT_DIR`; otherwise Git supplies the root. | Only an integer zero allows. Root discovery, missing entry, import, syntax, runtime and premature exit failures return 2 with a visible reason. Interpreter/shell launch failure or host timeout is outside this script's control. |
| `scripts/guard_entry.py` | Load the adjacent dispatcher by absolute path and call its `main`. | Reject missing/redirected dispatcher paths, exceptions and invalid/nonzero results. The checkout and installed interpreter remain trusted inputs; this is no tamper-resistant sandbox. |
| `scripts/hook_shell_routes.py` | Extract `command` from Bash, PowerShell and Monitor; `cmd` from exec_command; `command` from the exact compatibility route `mcp__terminal__run_in_terminal`. | Reject missing, empty, malformed and competing command fields. Ordinary MCP arguments stay opaque and retain tool-name policy. New tool aliases require their actual contract and tests. The terminal compatibility route does not attest an installed server. |
| Executor context | Use exec_command's `workdir` or the terminal route's `cwd` when resolving an accepted push's optional relative `git -C`. | Reject conflicting/unsupported directory aliases, invalid paths, drive-relative paths and network workdirs. No process-wide `chdir`. Absent/null context uses the session directory. |
| `scripts/preflight_push.py` | Resolve the accepted named push remote, query its explicit `https://github.com/owner/repo` target, then read any applicable standing grant. | Pin host against enterprise defaults and validate response shape, duplicate keys, canonical ASCII identity, recognized visibility and remote/response identity equality. PRIVATE passes this check; PUBLIC/INTERNAL require a matching grant. Unknown visibility always refuses. CLI, parse or grant-read failures refuse. |
| Antigravity shim | Capture the real adapter's response and require one valid decision with successful integer status. | Emit one normalized decision. Import/crash/premature-exit, noisy/duplicate/malformed JSON and invalid statuses become one DENY. Host interpretation and activation are separate checks. |

The accepted push grammar remains one standalone direct
`git [-C repository] push <named-remote> ...`. Unsupported repository selectors,
chaining and direct URL destinations are refused when recognized as pushes.
This is not a general parser for aliases, scripts, arbitrary shell programs or
all MCP operations. A private destination is not evidence that its content is
safe to expose, and a standing grant is not fresh authorization for a Git act.

## Verification and activation

Run the focused checks from the harness root:

```powershell
python -B -m unittest tests.test_guard_entry tests.test_hook_shell_routes tests.test_guard_wiring tests.test_guard_shim tests.test_hook_pretooluse tests.test_hook_mcp tests.test_settings_matcher tests.test_preflight_push
```

The tests execute the host-applicable configured commands against disposable
Git checkouts, drive real dispatcher call sites with controlled preflight
responses and test both ALLOW and refusal paths. No payload push is executed.
Missing dependencies, startup exits, cwd/PYTHONPATH decoys, exact stdin,
working-directory propagation and malformed responses have dedicated controls.
Keep failure receipts and run reversion/deleted-call controls in disposable
copies or in-memory modules, with source identity retained.

On the current Windows host, Claude's command and Codex's `commandWindows` can
be executed by the fixture. The portable Codex command has a structural check;
live POSIX execution remains unqualified until that runtime is available. A
green fixture does not establish that a desktop host has enabled its hooks.

The PreToolUse definitions have a 90-second host budget, above the declared
10-second root lookup, 10-second remote lookup, 30-second GitHub query and
10-second optional primary-checkout grant lookup waits.
A wiring check compares the configured budget with the declared subprocess
timeouts plus margin. It cannot bound arbitrary filesystem stalls, host
scheduling or a future unbounded call; host termination remains an acceptance
limit, even when the configured budget is sufficient for these declared waits.

Codex requires review/trust of changed hook definitions and may skip untrusted
definitions. After the local candidate passes review, the operator must inspect
and trust it using the host's supported hook UI (`/hooks` in the CLI), then
confirm a harmless allow/block probe on the actual host entry. Hook trust and
running state are not observable from these repository tests. Do not edit trust
hashes or bypass trust to make a result green. See the
[official hook documentation](https://learn.chatgpt.com/docs/hooks).

## Later hardening packages

These are proposals, not completed capabilities:

- A publication audit of selected content, all exposable Git refs/history,
  identities and hosting surfaces, with owner review before public release.
- Additional tool adapters only after observing their exact payload and context
  contracts; an execution broker would need its own authority and threat model.
- Hook activation checks on each supported host and shell, including native
  POSIX execution and host timeout/interpreter-failure behavior.
- Repository adoption and skill-routing refinements after separate source
  evidence and proportional review.

The current Phase 1 task record under `team/` owns the candidate, actual test
receipts, independent review, rollback bytes and remaining activation status.
Local implementation, reviewed candidate, delivery, host activation and reuse
are distinct states. No automatic Game dispatch or source edit follows a local
guard change.
