# Development Mapping intake

Use only fields relevant to the question. Keep current game facts in a dated
local record; this template grants no game or external authority.

## Question and route

- Question to answer: <who / prerequisite / order / current result / blocker>
- Facts cutoff and timezone: <observed through; sequential reads are not atomic>
- Game, project root, chat and host: <from current binding>
- Task/leaf and owner-maintained contract: <identity and path>
- Integrator and Studio operator: <identities; mapping does not take over>
- Exact candidate and receipt: <ID, paths and SHA-256; unknown stays unknown>
- Prior useful map and change trigger: <route / grant / handback / result / failure>
- Read scope: <named source/contracts/reports; no recursive audit by default>
- Mapping write scope: <own dated harness model/report only>
- Excluded scope and stop boundary: <preserve owner state and other projects>

## Model the relations

- Views needed: <scope / people / production / runtime / evidence>
- Stable entities: <ID, kind, label, owner, input, output, declared status>
- Basis of each claim: <observed source / recorded assignment / prescribed
  workflow / reviewed evidence / proposed work / recorded pending>
- Directed relation: <source, target, kind, readable meaning, feedback flag>
- Supporting references: <edge evidence IDs; record endpoint inheritance explicitly>
- Source identity: <path, SHA-256, read time, what was actually inspected>
- Open discrepancies: <old wording, newer explicit source and unresolved cells>
- Next responsible owner: <already-authorized action or proposal; no new dispatch>

Keep scope levels separate from production steps and evidence stages. An approval
is a recorded grant, not a completed implementation. A new candidate has its own
checks. A `depends-on` arrow points from dependent to prerequisite; other arrows
follow their named relation. Feedback loops are valid. Do not turn graph reach
or stage counts into proved impact, authority, a schedule or percent complete.

## Engine and handback

Follow [the schema and commands](../docs/roblox-development-network.md). Start a
fresh schema-version-1 JSON model from the
[fictional example](ROBLOX-DEVELOPMENT-MAP.example.json), then replace all example
identities, evidence and claims with the observed task. There is no automatic
source discovery or snapshot refresh.

```powershell
python scripts/roblox_development_map.py check --map team/<map>.local.json
python scripts/roblox_development_map.py trace --map team/<map>.local.json --node <id> --direction out --depth 2
python scripts/roblox_development_map.py compare --before team/<previous>.local.json --after team/<map>.local.json
python scripts/roblox_development_map.py report --map team/<map>.local.json --out team/development-maps/<new-report>.md
```

- Check result and actual commands: <structure; optional current evidence hashes>
- Relation review: <source/report coverage and unresolved interpretation>
- Changed nodes/relations: <candidate-specific differences; no inherited passes>
- Output paths: <dated JSON, new report, optional interactive explanation>
- Evidence and acceptance limits: <game / instrument / device / user / service>
- Cleanup and next mapping trigger: <meaningful event; idle means no re-audit>

Use the existing [candidate review](../scripts/roblox_review.py) for substantive
tool changes, [debug case](ROBLOX-DEBUG-CASE.template.md) for diagnosis and
[visual brief](ROBLOX-VISUAL-BRIEF.template.md) for capture/comparison work.
