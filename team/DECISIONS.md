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

Review methods were adapted on 2026-10-20 from the user's governance-os at the
pinned revision in the [adoption record](../docs/governance-os-adoption.md).
The [operating method](../docs/roblox-governance.md) documents their limits.
