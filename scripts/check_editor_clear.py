"""Block a headless engine launch while an interactive editor is running.

Mechanizes the never-concurrent-editors rule: two editor processes on one
project corrupt state in ways that surface later and elsewhere. Checks the
process list for names starting with the given prefix (default
UnrealEditor, covering UnrealEditor.exe and UnrealEditor-Cmd.exe).

Exit 0 = clear to launch. Exit 1 = an editor is running, or the process
enumerator failed (fail-closed: an empty or crashed listing is not
proof that no editor is running). Names / reason on stdout.
"""

from __future__ import annotations

import subprocess
import sys


class ProcessListError(Exception):
    """Process enumerator failed; callers must fail closed."""


def matching_processes(process_names: list[str], prefix: str) -> list[str]:
    """Pure core: which names match the editor prefix (case-insensitive)."""
    p = prefix.lower()
    return [n for n in process_names if n.lower().startswith(p)]


def list_processes() -> list[str]:
    try:
        if sys.platform == "win32":
            proc = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                                  capture_output=True, text=True, timeout=30)
        else:
            proc = subprocess.run(["ps", "-A", "-o", "comm="],
                                  capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ProcessListError(str(e)) from e
    if proc.returncode != 0:
        raise ProcessListError(
            f"process enumerator exited {proc.returncode}")
    if sys.platform == "win32":
        names = []
        for line in proc.stdout.splitlines():
            if line.startswith('"'):
                names.append(line.split('","')[0].lstrip('"'))
    else:
        names = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not names:
        # A machine with a working enumerator always has some processes.
        # Zero names means we parsed nothing, not "no editor".
        raise ProcessListError("process enumerator returned no names")
    return names


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    prefix = argv[1] if len(argv) > 1 else "UnrealEditor"
    try:
        hits = sorted(set(matching_processes(list_processes(), prefix)))
    except ProcessListError as e:
        print(f"LAUNCH BLOCKED: cannot enumerate processes ({e}). "
              "The never-concurrent-editors rule is fail-closed.")
        return 1
    if hits:
        print(f"LAUNCH BLOCKED: editor process(es) running: {', '.join(hits)}. "
              "The never-concurrent-editors rule: close the editor (or have "
              "the user close it and say go) before a headless launch.")
        return 1
    print(f"clear: no process matching '{prefix}*'")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
