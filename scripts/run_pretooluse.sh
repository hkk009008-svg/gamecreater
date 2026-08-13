#!/bin/sh
# Interpreter picker for the PreToolUse dispatcher.
# MUST exec the hook. An or-chain of interpreters treats the hook's
# blocking exit 2 as "try the next interpreter" and fails open.
set -u
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  dir=$CLAUDE_PROJECT_DIR
else
  dir=$(dirname "$0")/..
fi
hook=$dir/scripts/hook_pretooluse.py
if [ ! -f "$hook" ]; then
  echo "guard failed closed: hook not found at $hook" >&2
  exit 2
fi
for bin in python3 python py; do
  if command -v "$bin" >/dev/null 2>&1; then
    exec "$bin" "$hook"
  fi
done
echo "guard failed closed: no python3/python interpreter on PATH" >&2
exit 2
