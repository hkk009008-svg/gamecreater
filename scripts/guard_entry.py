"""Fail-closed entry for the adjacent PreToolUse dispatcher.

The hook configuration must protect loading this file as well. This entry pins
the dispatcher to its own saved checkout, then accepts only ``main()`` returning
the exact integer 0. It does not select a checkout from cwd or an environment
variable, interpret tool commands, or grant authority.
"""

import sys


def _blocked(reason: str) -> int:
    # A broken output stream must not turn a refusal into an exit-1 crash.
    try:
        print(f"guard-entry failed closed: {reason}", file=sys.stderr)
    except BaseException:
        pass
    return 2


def main() -> int:
    try:
        from pathlib import Path
        import runpy

        source = globals().get("__file__")
        if not isinstance(source, str) or not source or not Path(source).is_absolute():
            return _blocked("entry path is missing or is not absolute")
        entry = Path(source).resolve(strict=True)
        if (not entry.is_file() or entry.name != "guard_entry.py"
                or entry.parent.name != "scripts"):
            return _blocked("entry path does not identify scripts/guard_entry.py")
        target = entry.parent / "hook_pretooluse.py"
        if not target.is_file() or target.resolve(strict=True) != target:
            return _blocked("adjacent dispatcher is missing or resolves elsewhere")

        sys.path.insert(0, str(entry.parent))
        namespace = runpy.run_path(str(target), run_name="_gamecreater_pretooluse")
        dispatch = namespace.get("main")
        if not callable(dispatch):
            return _blocked("adjacent dispatcher has no callable main")
    except BaseException as exc:
        return _blocked(f"dispatcher load failed ({type(exc).__name__})")

    try:
        status = dispatch()
    except BaseException as exc:
        # SystemExit(0/None) here is premature termination, not a returned ALLOW.
        return _blocked(f"dispatcher execution failed ({type(exc).__name__})")
    if type(status) is not int:
        return _blocked("dispatcher did not return an integer status")
    if status != 0:
        return _blocked(f"dispatcher returned status {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
