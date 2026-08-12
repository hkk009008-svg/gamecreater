---
name: create-regression-pin
description: Author a strict-xfail regression pin for a confirmed-but-deferred defect, with the two recurring traps — assertion-shape and non-vacuous flip — as built-in checks. Use when a confirmed code defect is being left unfixed this session.
---

# Create a Regression Pin (strict-xfail)

## When
A confirmed defect you are NOT fixing this session must ship a
`pytest.mark.xfail(strict=True, reason=...)` pin in the same session — so
the test suite, not the next session's memory, re-verifies it. (Or label it
test-infeasible with a one-line reason in the arc record.)

## The pin (shape)
```python
@pytest.mark.xfail(strict=True, reason="<defect-id>: <one line>; see the defect register")
def test_<defect_id>_regression():
    # Assert the CORRECT (post-fix) behavior. strict=True means:
    #   defect present -> test fails  -> xfail  (expected)   -> suite stays green
    #   defect fixed   -> test passes -> XPASS  (unexpected) -> suite goes RED -> remove the pin
    ...
```

## Trap 1 — assertion shape must match how the fix will land
The pin's assertion dictates what "fixed" looks like. If the real fix will
make a **direct call return safely** (not raise), a pin written with
`pytest.raises(...)` will never flip to XPASS even after the fix — it keeps
passing as xfail forever. Match the assertion to the fix's contract:
- fix = "stop raising / return safe value" → assert the safe return
- fix = "start raising / start blocking" → `pytest.raises` / assert the block
- fix = "coerce bad input + warn, keep gate alive" → assert the coerced
  value AND that the gate still runs

## Trap 2 — prove the pin is non-vacuous
A pin that never actually exercises the defect is invisible-green theater.
Before you trust it:
- Run `python -m pytest <file> --runxfail -q` and confirm it goes **RED**
  against the current (unfixed) code — that proves the assertion really
  catches the defect.
- Confirm the failure reason is the defect, not a setup error or an import
  skip swallowing it.
- Confirm it would flip to XPASS once the fix lands (Trap 1's contract).

## Steps
1. Give the defect an ID in the game's open register, with its evidence.
2. Write the test asserting post-fix behavior (Trap 1).
3. Add the `xfail(strict=True, reason=…)` decorator citing the defect ID.
4. Run `--runxfail` and confirm RED with the right reason (Trap 2).
5. Run the normal suite slice and confirm it reports `xfailed` (not
   `xpassed`, not `error`).
6. Note the pin (`file::test_name`) beside the register entry, and commit.
   This pins a DEFERRED defect — it does not substitute for verifying a fix
   you DID land.

## When a pin is infeasible
If the defect cannot be expressed as a runtime test (needs a live GPU
session, a paid external API, non-deterministic output), label it
test-infeasible with a one-line reason in the register instead of forcing a
vacuous pin. An engine-side defect may still be pinnable one level down —
as an assertion in the probe script that exercises it.

## Provenance

Ported 2026-08-12 from the originating governance corpus, where deferred
defects re-verified by memory instead of CI recurred until strict pins made
the suite the reminder. The lock-management trap specific to that repo's
multi-seat protocol was dropped; assertion-shape and vacuity are universal.

## Changelog

- 2026-08-12 — Initial port; defect register generalized from that repo's
  remediation inventory, multi-seat lock trap removed.
