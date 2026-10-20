# Visual workbench checkpoint

As of 2026-10-20. This checkpoint covers the reusable harness tooling and its
documentation. It does not change the bound game's release state or roadmap.
The user authorized committing and pushing this scope to the existing origin.

## Delivered scope

- `scripts/roblox_visual_packet.py`: init, check and build commands; strict
  manifests, original-media hashes, comparison prerequisites and fresh output.
- `scripts/roblox_visual_html.py`: offline review page with visual intent,
  original frames, eligible overlay, approximately paired video, settings,
  evidence gaps, coverage and recorded decisions.
- Focused tests, visual workflow and workbench guides, brief and JSON templates,
  README entry points, generated-packet ignore rule and two visual lessons.

The tool uses Python and Pillow. Its reusable path/schema helpers already live
in the committed review module. Local capture manifests and generated packets
stay ignored; the public source does not include the game's image/video bytes.

## Verification and closed work

- **WORKBENCH-IMPLEMENTATION — closed:** 29 focused tests run, 28 passed and
  one actual-symlink test skipped because this Windows host lacks creation
  privileges. The deterministic reparse rejection test passed.
- **INDEPENDENT-REVIEW — closed:** GO on the recorded implementation, tests,
  workbench guide and template, with 15 additional adversarial probes passed.
  Review found and verified fixes for wrong-size control evidence, contradictory
  capture modes, still-image containers classified as video and unsafe paths.
- **BROWSER-CONTROLS — closed for inspected examples:** image comparison
  navigation and 75% overlay reveal worked. Historical videos advanced and
  paused through paired controls. Gap disclosure and disabled overlay behavior
  worked at the actual 508-pixel browser width, without horizontal overflow.
- **ORIGINAL-IDENTITY — closed for the local study:** four copied media hashes
  match the report; the bundled manifest is byte-identical to its source.
  The Windows legacy-console Unicode failure is fixed and regression-tested.

Detailed local receipts, retained outside Git:
`team/visual-core-validation-20261020T144255377262Z.local.json`,
`team/visual-example-evidence-review-final-20261020T144311548193Z.local.json`,
`team/visual-workbench-final-cli-20261020T144554347227Z.local.json`,
and `team/visual-workbench-handoff-20261020.local.md`.
They describe the implementation session; a new candidate needs its own checks.

## Open register and next executable action

- **Blocks controlled comparison of the historical game study:** recorded
  viewport versus decoded image dimensions differ; device/random-state
  metadata and some map/motion/device coverage are absent. Its report remains
  `needs-evidence`; those gaps do not prevent ordinary visual critique.
- **Blocks game-quality acceptance:** this harness work establishes no native
  gameplay, physical-device performance or user visual acceptance. Game's
  owner retains that implementation and acceptance work.
- **No blocker to local workbench use:** start a scoped study with
  `python scripts/roblox_visual_packet.py init --help`, supply original media,
  and complete measured metadata using the [guide](../docs/roblox-visual-workbench.md).
  `ready-for-review` is conditional metadata eligibility, never a beauty score.

No new game task starts from this checkpoint. Read the current game binding and
owner's NOW before game implementation or Studio operations. Git refs and the
delivery receipt establish whether this authorized commit reached origin.
