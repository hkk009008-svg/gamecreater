# The long-horizon arc model

Game work stretches over months and hundreds of sessions. The unit of
progress is not the session (too small — sessions end mid-thought) and not
the project (too big — nothing ever "finishes"). It is the **arc**: one
objective pursued until an observable phase-change signal ends it.

## Three modes, smallest that fits

**Ordinary work declares nothing.** A bug fix, a probe, a parameter sweep
inside an existing arc — just do it, with skills and evidence discipline.
Ceremony added to ordinary work is how systems stop being used.

**Explore** — the default for campaigns. One arc brief
(`memory/ARC-BRIEF.template.md`): objective, sandbox, protected boundary,
phase-change signal. Attempts are recorded as they run — command, result,
evidence ref — and failures stay in the log, because a failure not written
down gets re-run by a later session at full price. Explore results are
provisional: they guide the next attempt, they are not accepted claims.

**Validate** — freezing one candidate. Inputs, code, thresholds, and
environment pinned; evidence generated against the frozen contract; the
claim gets a real review. A negative result is an acceptable outcome and
is recorded as knowledge.

**Promote** — touching canonical or live state. Needs the reviewed
candidate, a rollback point established *before* the mutation, and the
user's separate, exact authorization for the write. A mode label never
supplies authority; neither does a passing gate.

## The rhythm of an arc

1. **Open** — write the brief; add the arc to `NOW.md`.
2. **Work** — attempts, evidence, lessons appended to the inbox as they
   are paid for. Register items get tiered by what they block, and the
   tiers are worked in order — depth-first on the most interesting item
   is a recorded, expensive failure mode.
3. **Checkpoint** — at every hold: `NOW.md` current, lessons swept,
   committed. Cheap, mandatory, and the reason session boundaries stop
   mattering.
4. **Close** — the phase-change signal fires; run `distill-an-arc`:
   sweep the inboxes, propose skill edits with evidence, apply on the
   user's go, update `NOW.md` to the next arc.

## Verification stance (the short version every arc inherits)

- A gate proves nothing unless it runs the consumer's actual entry path.
- Execution status and output status are different facts; report both.
- A zero needs a known-positive on the same instrument before it means
  absence.
- Works-here-fails-there gets an enumerated difference list and
  discriminating reads, not a patch at the likeliest suspect.
- Visual verdicts belong to the user; attach the frame every time a claim
  rests on how something looks.

## Authority stance

External effects — push, merge, publish, canonical writes, paid tools,
deletions — are each separately authorized, per act, by the user. Standing
grants live in `GAME.local.md` and cover exactly what they name. When a
guard blocks an action, the guard is right until the user says otherwise.
