"""Block a headless engine launch while an interactive editor is running.

Mechanizes the never-concurrent-editors rule: two editor processes on one
project corrupt state in ways that surface later and elsewhere. Checks the
process list for names starting with the given prefix (default
UnrealEditor, covering UnrealEditor.exe and UnrealEditor-Cmd.exe).

Exit 0 = clear to launch. Exit 1 = an editor is running (names on stdout).
"""

from __future__ import annotations

import subprocess
import sys


def matching_processes(process_names: list[str], prefix: str) -> list[str]:
    """Pure core: which names match the editor prefix (case-insensitive)."""
    p = prefix.lower()
    return [n for n in process_names if n.lower().startswith(p)]


def list_processes() -> list[str]:
    if sys.platform == "win32":
        proc = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                              capture_output=True, text=True, timeout=30)
        names = []
        for line in proc.stdout.splitlines():
            if line.startswith('"'):
                names.append(line.split('","')[0].lstrip('"'))
        return names
    proc = subprocess.run(["ps", "-A", "-o", "comm="],
                          capture_output=True, text=True, timeout=30)
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def main(argv: list[str]) -> int:
    prefix = argv[1] if len(argv) > 1 else "UnrealEditor"
    hits = sorted(set(matching_processes(list_processes(), prefix)))
    if hits:
        print(f"LAUNCH BLOCKED: editor process(es) running: {', '.join(hits)}. "
              "The never-concurrent-editors rule: close the editor (or have "
              "the user close it and say go) before a headless launch.")
        return 1
    print(f"clear: no process matching '{prefix}*'")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
