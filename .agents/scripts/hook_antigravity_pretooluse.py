"""Shim: the path Antigravity actually looks for.

`.agents/hooks.json` declares `python scripts/hook_antigravity_pretooluse.py`.
Antigravity resolves that relative to the hooks file's own directory, not to
the repo root, so it looked for

    c:\\gamecreater\\.agents\\scripts\\hook_antigravity_pretooluse.py

and failed with `[Errno 2] No such file or directory` -- 13 times between
04:42:39 and 04:43:35 on 2026-08-14, logged at
%APPDATA%/Antigravity/logs/language_server.log:112-213. Antigravity logs the
failure and lets the tool call proceed, so BOTH mechanized rules (push
preflight, editor-clear) were unguarded on that harness for the whole window
-- including 04:43:06, the second commit ffc5212 landed.

Fixing this by writing an absolute path into hooks.json would work and would
also bake this machine's user name into a tracked file in a PUBLIC repo. A
shim at the path Antigravity already looks for costs nothing and leaves both
resolutions working: if some other Antigravity version resolves against the
repo root instead, it finds the real script directly.

Fails CLOSED. If the real dispatcher cannot be imported, this denies rather
than allowing -- the whole point is that a broken guard must not read as a
permissive one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REAL = Path(__file__).resolve().parent.parent.parent / "scripts"


def deny(reason: str) -> int:
    print(json.dumps({"decision": "deny", "reason": reason}))
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if not REAL.is_dir():
        return deny(f"guard shim failed closed: no scripts dir at {REAL}")
    sys.path.insert(0, str(REAL))
    try:
        import hook_antigravity_pretooluse as real
    except Exception as e:                                      # noqa: BLE001
        return deny(f"guard shim failed closed: {type(e).__name__}: {e}")
    return real.main()


if __name__ == "__main__":
    sys.exit(main())
