# Current team decisions

Only reusable decisions that still shape the Roblox team belong here.
Current game versions, active owners and run results belong in NOW and local
task records. Revisit a decision when its stated condition changes.

| Decision | Reason | Revisit when |
|---|---|---|
| Game source/builds stay in the bound project; this repo owns methods and coordination | Keeps live implementation separate from reusable knowledge | A game explicitly migrates its source of truth |
| One integrator owns shared files/builds; one operator owns each Studio mutation session | Shared state makes overlapping writes and input unsafe for useful parallel work | An exercised mechanism can safely isolate the affected state |
| Review follows changed behavior; ordinary local work needs no packet | Focus review on meaningful failures | Recurring defects show classification misses a boundary |
| Substantial review binds selected source, saved build and evidence bytes | Historical results cannot accept changed candidates; the game need not use Git | An adopted release system supplies stronger exact-version binding |
| Evidence and user acceptance remain separate stages | Compilation, screenshots and scripts answer different questions from gameplay/devices | A specific test actually exercises an additional stage |
| Use existing collaboration tools; messages are distinct from agreement/authority | Another transport is unnecessary without a demonstrated gap | Delivery/coordination failures justify a scoped replacement |
| Reviewer verdicts never grant publication, purchases, destruction or Git outward actions | Correctness and authority for an effect are separate facts | The user supplies applicable authority, not a change to this principle |
| Scale concurrency to independent ready work and integration capacity | A small effective team avoids duplicate writers and idle coordination; user-authorized worker chats use exact task boundaries | Observed dependency, waiting or integration costs justify changing the team size |
| Derive specialized modification/debugging engines from actual cases and controls | Reusable methods should retain proven mechanisms, failed hypotheses, instrument limits and reproducible results | Repeated new production evidence supports a new adapter or changes its supported contract |

Review methods were adapted on 2026-10-20 from the user's governance-os at the
pinned revision in the [adoption record](../docs/governance-os-adoption.md).
The [operating method](../docs/roblox-governance.md) documents their limits.

The balanced-concurrency and evidence-based specialization decisions were made
explicit at the user's request on 2026-10-21. See the
[engine contracts](../docs/roblox-workflow-engines.md) for the working design;
new engine orchestration remains a proposal until implemented and demonstrated.
