# Roblox team handoff — <change or release candidate>

As of: <date, time and timezone>

## Outcome and durable state

- Game and task/release: <bound game and identifier>
- Implementation/integration owner: <owner>
- Result: <implemented / partial / blocked; concrete player-visible behavior>
- Changed paths: <exact files or bounded Edit paths>
- Source of truth: <source-built inputs or saved Studio-native document>
- Saved build: <absolute path; or none produced>
- Build hash and input receipt: <exact values/paths or unavailable>
- Predecessor/rollback: <preserved build/backup and restoration action>
- Existing unrelated work: <relevant ownership/collision note>

## Acceptance results

Use PASS, FAIL, NOT RUN, BLOCKED or USER PENDING. Omit irrelevant rows or explain
why they are unnecessary. Passing source checks do not close later stages.

| Stage | Status | Exact entry/setup and result | Evidence / limitation |
|---|---|---|---|
| Source/rules | <status> | <actual modules/checks> | <report; doubles if used> |
| Saved build | <status> | <serialized inputs/content checked> | <receipt> |
| Cold ordinary entry | <status> | <saved file; lobby/spawn/Practice/match/return> | <log/readback> |
| Multiplayer | <status> | <actual independent clients and flows> | <evidence or untested cells> |
| Presentation/emulation | <status> | <capture/motion/device layout> | <scope sampled> |
| Physical device | <status> | <device/input/performance> | <actual evidence> |
| User acceptance | <status> | <verbatim relevant verdict> | <pending question if any> |
| Published service | <status> | <released version/account paths> | <actual evidence> |

- Open failures and what they block: <playing / release / quality / optional>
- Invalid or superseded instruments: <failed setup/fixture and replacement>
- Source changes after checks: <affected checks rerun or remaining gap>
- Review class, non-author and verdict: <reason; actual reviewer; GO / NITS / FAIL / pending>
- Exact candidate/review pair: <paths and fresh check result; or ordinary-local not needed>
- Superseded candidate/review and remediation: <retained paths; explicit resolution or none>

A review does not close NOT RUN stages or authorize publication. The candidate
checker validates only the supplied pair, not all historical reviews; reconcile
any prior FAIL explicitly. See docs/roblox-governance.md.

## Studio and cleanup

- Last observed Studio file/place, ID and mode: <current observation, not a guarantee>
- Operator and handback: <who may mutate next and condition>
- Temporary fixtures/camera/simulator changes: <removed/restored or outstanding>
- Unsaved/live-only state: <captured or explicit blocker>
- User play session: <untouched / authorized actions and resulting state>

## Publishing and account-owner steps

Include when delivering a release. Use verified identifiers; keep unknowns
blank/unavailable rather than inventing them. Recheck relevant current official
Roblox documentation when performing publication/account/policy-dependent work.

- Intended account/group: <verified owner or owner decision needed>
- Universe ID / Place ID: <verified values and source>
- Official requirements checked: <dated direct links, or pending at execution>
- Resource mapping/return file: <pass/product/audio/image IDs and permissions>
- Commerce state: <sales flags; owned equip vs new-purchase eligibility>
- Activation build: <verified mappings, exact saved build/version or pending>
- Publication authority/executor: <exact grant and target, or owner action pending>
- Sales enablement: <intended timing and executor>
- Live checks remaining: <buy, cancel/failure, owned equip, rejoin as relevant>
- Uploads/private servers/other owner setup: <remaining actions or none>
- Purchase/spend authority: <specific authorized test or no charge performed>
- Recovery after failed release: <preserved predecessor and concrete response>

| Remaining action | Executor | Prerequisite / authorization | Completion evidence |
|---|---|---|---|
| <owner setup> | <owner> | <verified resource/permission> | <receipt/returned IDs> |
| <activation build/publication> | <owner/integrator> | <exact authority and tests> | <version/build> |
| <published service check> | <owner/tester> | <authorized account/purchase> | <observed result> |

## Next executable action

<One concrete file, command or ordinary entry path, owner and expected result.
State what can proceed independently if a dependency is pending.>

- Team coordination updated: <team/NOW.md / task state>
- Game current state updated by its owner: <bound NOW.md or pending handback>
- Lessons recorded: <inbox/entry or no new lesson>
- Git state/action: <applicable repo and authorized action; no invented commit>
