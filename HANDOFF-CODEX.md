# Handoff — Kurogane no Onryo (for the Codex side)

**Written:** 2026-08-16, by the Claude side, at the user's request.
**Scope:** everything needed to pick up game work cold on this machine —
where the plan/direction files live, the rules that bind every agent, the
current state, and the traps already paid for.

---

## 1. Orientation — read these, in this order

| # | File | What it is |
|---|------|-----------|
| 1 | `C:\gamecreater\CLAUDE.md` | **The session router.** Work protocol, authorization boundary, engine modes, run-verdict discipline. Written for Claude but the RULES bind any agent. |
| 2 | `C:\gamecreater\GAME.local.md` | Active game pointer: roots, engine path, repos, standing grants. |
| 3 | `D:\Unreal\game\kurogane\NOW.md` | **Current truth.** The open register (tiered by what each item blocks), next executable action, standing facts, vendor re-apply list. If NOW.md and chat memory disagree, NOW.md wins; if NOW.md and the assets disagree, the assets win and NOW.md gets corrected. |
| 4 | `D:\Unreal\game\kurogane\LESSONS.md` | Game lessons inbox (58 entries), **append-only**. Every trap in §6 has a full entry here with evidence. |
| 5 | `C:\gamecreater\memory\LESSONS.md` | Harness-general lessons inbox (50 entries), **append-only**. |

Direction/plan files beyond the register:

| File | Content |
|------|---------|
| `D:\Kurogane\Experiments\Combat\RECON-2026-08-16.md` | Read-only recon: hair color binding chain, sweep-instrument documentation, **KG-RESPAWN-1 swap plan**, **KG-IMPACT-1 native-channel verdict table**. |
| `C:\gamecreater\skills\<tier>\<name>\SKILL.md` | 26 canonical skills — each is a work protocol paid for by a real failure (its Provenance section names which). Work from them; don't re-derive. |
| `C:\gamecreater\templates\` | Arc-brief and GAME.local templates. |
| `D:\Kurogane\Experiments\Playtest-2026-08-13\` | FIXES.md, HAIR-TATTOO.md — prior arc evidence. |

## 2. Machine layout

Three git repos, distinct roles:

| Repo | Path | Role | State at handoff |
|------|------|------|------------------|
| gamecreater | `C:\gamecreater` | Harness/OS: router, skills, scripts, guards, harness lessons | main, in sync after this commit |
| Unreal | `D:\Unreal` | Working root: probe/sweep/apply scripts, NOW.md, game lessons | main, **2 unpushed commits** (2a0f7ac, 4ac3d53) — the work exists on one disk only until the user authorizes a push |
| Kurogane | `D:\Kurogane` | UE 5.8 project. `Content/` is allowlist-tracked; vendor (`Content/Hyper`, GDH) and `Content/Kurogane/Experiments` are NOT in git | main, clean |

Engine: UE 5.8 at `D:\UE_5.8\`. Project: `D:\Kurogane\Kurogane.uproject`.
Map that matters: `/Game/Kurogane/Gameplay/Maps/L_Kurogane_PlayTest`.
Player pawn: `/Game/Kurogane/Gameplay/BP_Kurogane_Combat` (parent
`CH_Male_Combat` from the Hyper kit). **There is no placed pawn in the
map** — the pawn exists only after a real GameMode spawn (PIE).

## 3. Hard rules — read before acting

The Claude harness enforces some of these with PreToolUse hooks. **Codex
gets no mechanical guard — these bind by discipline alone.**

1. **Per-act authorization from the user, every time**, for: `git push`,
   `git merge`, making anything public/publishing, deleting or
   overwriting an existing asset/render/evidence file, any DCC launch
   (Blender etc.), any paid/provider tool, and **any canonical
   `Content/` write**. A plan, a mode, or "let's resume" grants none of
   these. Standing grants (no ask): read under the named roots, headless
   engine launches for captures/probes, writing scripts/renders/logs/docs
   under `D:\Unreal`, `git add`/`commit` there.
2. **Never two editors / never headless while an editor is open.**
   Declare mode with `python C:\gamecreater\scripts\mcp_session.py
   on|off|status`. Check with `python C:\gamecreater\scripts\engine_run.py
   mode`.
3. **Never hand-write an `UnrealEditor-Cmd` line.** Launch through the
   supervisor: `python C:\gamecreater\scripts\engine_run.py headless
   <script.py> --needs-rhi --artifact <out>\report.json --wall 900
   --stall 300`. It adds the right flags, watches two independent timers,
   kills the whole process tree, and writes a sidecar.
4. **Never quote a run that is not CITABLE.** `scripts/run_verdict.py`
   separates EXECUTION (engine finished) from OUTPUT (artifact landed and
   does not self-report failure). A script's `=PASS` sentinel is evidence
   about the script only. A crash is found by scanning the log BODY,
   never the tail. An artifact that exists but says FAIL is
   PRESENT_BUT_FAILING, not evidence.
5. **Lessons inboxes are append-only** (`>>` only; truncation is a
   violation the startup check reports). Append a lesson the moment it is
   paid for. Skill bodies change only at arc end, on the user's go.
6. **Backups before any destructive write**, sha256'd, and the backup's
   existence proven (read it back) before the write. Rollbacks live under
   `D:\Kurogane\Experiments\Combat\*_backup*\`.
7. **Vendor edits are not in git.** Anything changed under
   `Content/Hyper` or other untracked paths goes on the **re-apply list
   in NOW.md** with its rollback dir and re-apply script.

## 4. State at handoff (2026-08-16)

**Done and verified today:**
- **KG-HAIR-1 CLOSED (machine-side).** Hair grade 01 persisted into
  `MI_Hair` (`hairMelanin 0.97, hairRedness 0.16, Desat 0.14,
  WhiteAmount 0.20`) — CITABLE apply (`hair-apply-v1`), CITABLE cold
  verify on the real entry (`hair-cold-v1`). Rollback:
  `Experiments/Combat/hair_backup1/`. Re-apply:
  `D:\Unreal\Art\Characters\Kurogane\Scripts\LookDevV1\apply_hair_color_v1.py`.
  Decision sheets: `Experiments/Combat/hair-sweep-v7/front_hair_sheet.png`
  + `back_hair_sheet.png`.
- **KG-RESPAWN-1 mechanism PROVEN** (`downed-probe-v3`, CITABLE):
  Death Behavior=Downed → lethal hit → health becomes exactly 50, anim
  swaps to ABP_Downed_C, same actor, **no world reset**. Two persist
  routes measured shut: per-instance writes refused (variable not
  instance-editable), vendor-CDO flip would down enemies too.
- Combat damage (KG-DMG-1), feel pass, grip height, root-motion montage
  rebuild: all applied earlier and user-confirmed except the RM replay.

**Waiting on the USER (do not proceed without them):**
1. The 2-minute editor step that finishes KG-RESPAWN-1 — spelled out in
   NOW.md "Next executable action" (BeginPlay setter node in
   BP_Kurogane_Combat; pawn-BP edits are editor-only, see trap #1).
2. Playtest verdicts: combo glide after the RM rebuild, crouch camera
   observation, L lock-on, hair color in their own session, whether the
   On-Die widget still appears once Downed is persisted.
3. KG-TONE-1 face-tone pick (`tone-sweep-v8/front_tone_sheet.png`).
4. Authorization to push the 2 unpushed Unreal commits.

**Open, unblocked for an agent:** KG-IMPACT-1 tuning is data-asset work
(see recon §4 — shake/dilation are native and per-combo); KG-CLEAN-1/2/3
are hygiene. Task "repair 6 drifted skill citations" is gated on the
user-invoked distill ritual — leave it.

## 5. How work is done here

- **Scripts live in** `D:\Unreal\Art\Characters\Kurogane\Scripts\LookDevV1\`
  (capture/look-dev) and `D:\Unreal\harness\bin\` (gameplay probes).
  Convention: versioned files (`*_v1..vN`), each docstring records the
  failure the version fixes. Copy the newest version's patterns —
  especially `sweep_hair_color_v7.py` (the working PIE capture recipe)
  and `probe_downed_v3.py` (runtime probe + CDO flip pattern).
- **Every run**: env var for output dir (prefix `KUROGANE_` so the
  sidecar records it), a JSON artifact with its own gates, a sentinel
  scoped "execution-of-this-script-only", launched via `engine_run.py`.
- **Evidence** accumulates under `D:\Kurogane\Experiments\Combat\<run>\`.
  Contact sheets via
  `LookDevV1\compose_sheet_v1.py <dir> <out.png> --pattern ... --cols 4`.
- **Reading BP/asset internals headlessly**: UE Python does not expose BP
  editor arrays. Sanctioned fallback: name-table byte scan —
  `re.finditer(rb'([\x20-\x7e]{4,80})\x00', data)` over the `.uasset`.
- Console is Korean cp949: set `PYTHONIOENCODING=utf-8`, print ASCII.

## 6. Traps already paid for (do not pay again)

Full entries with evidence in `D:\Unreal\game\kurogane\LESSONS.md`.

1. **Headless saves of component-bearing Blueprints STRIP the pawn's
   SCS components** (with AND without `compile_blueprint`; proven twice,
   auto-restored). Pawn-BP edits happen in the live editor by the user's
   hands, full stop. Safe headless-save families: montages,
   AnimSequences, MICs, DataTables.
2. **`unreal.Rotator(a,b,c)` is (ROLL, PITCH, YAW)** in Python. Keyword
   args everywhere; aim cameras with
   `MathLibrary.find_look_at_rotation`.
3. **`save_asset` lies**: needs `mark_package_dirty()` +
   `only_if_is_dirty=False`, then byte-verify against a backup sha.
4. **`MaterialEditingLibrary.set_material_instance_scalar_parameter_value`
   returns False on success.** Gate on readback, never the return.
5. **`set_game_paused(True)` freezes render-state propagation** — camera
   moves, hides, MID writes all stop reaching the GPU while CPU-side
   readbacks stay green. Freeze the subject instead:
   `pawn.custom_time_dilation = 0.001`.
6. **Headless PIE SceneCapture renders black** except with the proven
   recipe: `RTF_RGBA8_SRGB` target created with a clear color,
   `always_persist_rendering_state=True` set BEFORE `texture_target`, NO
   post-process override, 3× `capture_scene()`, export with the capture
   actor as context. Prove the pixel reader first (clear RT to red, read
   it back), and read pixels in-engine via
   `RenderingLibrary.read_render_target_pixel`.
7. **`GroomComponent` has no `.bounds`** — use
   `SystemLibrary.get_component_bounds(c)` which returns THREE values
   (origin, extent, radius). Prove any bounds gate on the body mesh
   (known positive) before trusting it on a groom.
8. **BP enum properties want the enum MEMBER object** (`type(cur).DOWNED`),
   not an int or name. A variable without instance-editable refuses all
   runtime instance writes ("cannot be edited on instances") — probe via
   CDO edit + console `RestartLevel` (in-process memory, no asset touch).
9. **Never pass `/Game/...` paths through an MSYS/Git-Bash command line**
   — rewritten to `C:/Program Files/Git/Game/...`. Use env vars,
   PowerShell, or `MSYS_NO_PATHCONV=1`.
10. **Health is a GameplayTag-keyed map** on
    `AC_CH_Attribute_Manager_Base_C` — read
    `get_editor_property("Current Health")`; BP members are reached by
    NAME, never `dir()`. Damage route for probes:
    `GameplayStatics.apply_damage`.
11. **A sentinel/=PASS has never seen a pixel.** Gates that only ask
    "did bytes change" pass black frames (35 distinct shas of pure black,
    measured). Every capture gate must include an in-engine pixel truth
    or an offline mean vs a no-subject control frame from the same run.
12. **`Ctrl+S` in the editor saves the LEVEL, not the open Blueprint** —
    the BP editor's own toolbar Save (or Save All) is the one that
    persists; verify by file mtime + sha.

## 7. If something here contradicts the code or assets

The code/assets win. Record the conflict as a lessons-inbox append (rule
5) and correct NOW.md in the same session. Do not silently work around a
skill or this handoff — surface it to the user.
