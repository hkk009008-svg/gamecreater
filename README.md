# Roblox game-making team

gamecreater is the control repository for a Roblox game team. It coordinates
design, server gameplay, client/UI, world/art/audio, QA and release work while
each game keeps its own source, saved places and evidence.

Start with [AGENTS.md](AGENTS.md), [team/NOW.md](team/NOW.md) and machine-local
GAME.local.md. The current project is Strikepoint. The existing Shooter chat
retains ownership of its active release pass.

```powershell
python scripts/session_start.py
python scripts/roblox_team.py status
python scripts/roblox_team.py check
```

The [team operating guide](docs/roblox-team.md) defines production roles, exact file
assignments, one Studio operator and the acceptance stages. Use the
[task template](templates/ROBLOX-TASK.template.md) for delegation and the
[handoff template](templates/ROBLOX-HANDOFF.template.md) for release delivery.
Agents work in parallel where file/runtime ownership permits; one integrator
assembles and tests the playable result.

[Review and decisions](docs/roblox-governance.md) adds proportional review and
candidate checks adapted from your governance-os repository. Substantial
changes can bind a review to exact source, saved-build and evidence bytes;
changed or missing files invalidate the snapshot. Ordinary local edits keep
focused checks. The [adoption record](docs/governance-os-adoption.md) gives the
pinned revision, selections and limits; [team decisions](team/DECISIONS.md)
keep the durable rationale.

```powershell
python scripts/roblox_review.py --help
```

## Methods come from the working game

The initial method set comes from the actual source, build wrappers, scope
receipts, tests, Studio observations and lessons in the working Roblox game.
Local team/strikepoint-system.local.md and team/strikepoint-pipeline.local.md
dossiers explain that implementation and its limits. Recheck linked files before
acting: they describe dated observations, not permanent game state.

The [Development Mapping department](docs/roblox-development-network.md) maps
who owns each piece, what depends on it, how work passes between steps and which
evidence still blocks the result. Its separate offline engine checks an authored
relation graph, traces connections, compares snapshots and writes new reports.
Use the [mapping intake](templates/ROBLOX-DEVELOPMENT-MAP.template.md) for a
requested process/order map or a substantial dependency question:

```powershell
python scripts/roblox_development_map.py --help
```

The mapping department reads the game and maintains its own harness records.
Game retains integration, dispatch, Studio and active state ownership.

```powershell
python scripts/roblox_team.py inventory
```

This writes a fresh ignored JSON index of project files, sizes/timestamps,
source/tooling/document fingerprints, source mappings and evidence-directory
counts. It does not build, play, publish, upload, purchase or modify the game.
An inventory helps navigate and compare evidence; it does not establish that
every artifact was read or every feature works. Reusable methods live in skills/
and docs/; volatile project data stays local.

For visual quality, the [visual production workflow](docs/roblox-visual-quality.md)
turns art direction into a bounded gameplay slice, controlled image/motion
comparisons and measured device budgets. Use its
[short brief](templates/ROBLOX-VISUAL-BRIEF.template.md) with the existing task
contract; automated checks support the visual judgement without replacing it.

The [visual workbench](docs/roblox-visual-workbench.md) builds an offline review
page from original images or video. It carries the art brief, comparison controls,
capture settings, evidence gaps, coverage and the recorded decision together:

```powershell
python scripts/roblox_visual_packet.py init --media <before.png> --media <after.png> --out team/visual-study.local.json
python scripts/roblox_visual_packet.py check --manifest team/visual-study.local.json
python scripts/roblox_visual_packet.py build --manifest team/visual-study.local.json --out team/visual-packets/visual-study-001
```

Edit the generated manifest with actual capture settings before checking it.
Unknown settings stay unknown. A packet with gaps remains useful for critique;
only eligible comparisons enable the matched-image overlay. Generated packets
and local manifests are ignored by Git.

## Skills and checks

skills/roblox/build-roblox-game/SKILL.md is the Roblox entry.
[Skill routing](docs/skill-routing.md) preserves shared methods and inactive
Unreal skills without mixing engine procedures.

```powershell
python scripts/sync_skills.py --check
python -m unittest discover -s tests -p "test_*.py"
```

Use the actual game's reviewed build wrapper and current receipts. Do not replay
a historical build command or arbitrary fixture, or assume the newest place is
an accepted release. Source checks, saved builds, cold runtime, independent
clients, emulation, physical devices and user acceptance answer different questions.

## Existing projects and permissions

The old local binding is in the conversion backup. Historical Unreal tools,
skills and projects remain separate and inactive. Unreal entry commands refuse
execution while a Roblox game is bound. Rebinding a previous game requires its
own current task and grants.

Publication, account changes, purchases, uploads, paid providers and Git outward
actions require exact authority. The team protocol coordinates file/Studio
ownership; it is not a runtime lock. The existing .codex/hooks.json is retained;
its presence does not prove the app currently trusts or runs it.
