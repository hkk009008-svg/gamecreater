# Claude compatibility

Read and follow [`AGENTS.md`](AGENTS.md). It is the authoritative session
router, work policy, and authorization boundary for this repository.

Claude-specific lifecycle wiring lives in `.claude/settings.json`. It runs the
same session-start orientation and pre-tool guards used by the repository; this
file adds no separate policy.
