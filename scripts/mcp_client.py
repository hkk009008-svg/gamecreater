"""Speak MCP to the live Unreal editor from a plain Python process.

    python scripts/mcp_client.py handshake
    python scripts/mcp_client.py toolsets
    python scripts/mcp_client.py describe <Toolset.Name>
    python scripts/mcp_client.py call <Toolset.Name> <ToolName> '<json args>'
    python scripts/mcp_client.py capture-editor <out.png>
    python scripts/mcp_client.py capture-asset <assetPath> <out.png>

WHY THIS EXISTS, given the harness has native MCP tools. Two reasons, both
measured on 2026-08-14:

  1. `.mcp.json` is read at CLIENT STARTUP. Writing it mid-session enables
     nothing until the client restarts, so a session that just turned MCP on
     cannot use the very server it configured. This module needs no restart.
  2. An open TCP port proves a listener, not a protocol. Only a real
     `initialize` handshake proves the thing on 8000 speaks MCP, and
     `engine_run.py mcp-check` now uses this module to make that claim
     measured instead of inferred.

AUTHORITY. An MCP call is not a lesser act than a Python one. CLAUDE.md
reserves canonical `Content/` writes, deletions, publishing and DCC launches
for per-act authorization, and calling them through a toolset does not
change that. This module ships read-only helpers only; RESERVED_RE below
refuses the obvious destructive names as a backstop, not as a substitute for
asking.

PLUGIN QUIRKS worth knowing before you debug your own arguments:

  - EVERY parameter is effectively REQUIRED, whatever `inputSchema.required`
    says. `CaptureViewport` advertises no required params and its own
    description calls `captureTransform` optional ("If unset, uses the
    viewport's current camera"); calling it with `{}` fails with
    `input param "captureTransform" needs a default value`, and supplying
    only that one then fails the same way on `annotations`. Read `required`
    as a lower bound.
  - Images come back JSON-WRAPPED IN A TEXT BLOCK, not as an MCP `image`
    content block: `{"returnValue": {"mimeType": ..., "data": <base64>}}`.
    A client that only handles `type == "image"` silently finds nothing.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "http://127.0.0.1:8000/mcp"
PROTOCOL = "2025-06-18"

# Backstop only. The authorization boundary is CLAUDE.md, not this regex.
RESERVED_RE = re.compile(
    r"(delete|destroy|remove|publish|push|merge|deploy|cook|package"
    r"|savepackage|save_all|setvisibility)", re.IGNORECASE)


class McpError(RuntimeError):
    pass


def endpoint_from_config(cfg_path: Path | None = None) -> str:
    """Read the URL from .mcp.json so this client cannot drift from the one
    the harness itself would use."""
    cfg_path = cfg_path or (ROOT / ".mcp.json")
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return cfg["mcpServers"]["unreal-mcp"]["url"]
    except Exception:
        return DEFAULT_URL


class Mcp:
    def __init__(self, url: str | None = None, timeout: int = 120):
        self.url = url or endpoint_from_config()
        self.timeout = timeout
        self.sid: str | None = None
        self.server_info: dict = {}
        self._id = 0

    # -- transport --------------------------------------------------------
    def _post(self, payload: dict) -> tuple[int, dict, str]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        # Streamable HTTP may answer as JSON or as an SSE frame.
        req.add_header("Accept", "application/json, text/event-stream")
        if self.sid:
            req.add_header("Mcp-Session-Id", self.sid)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
        except OSError as e:
            raise McpError(f"cannot reach {self.url}: {e}") from e

    @staticmethod
    def _parse(raw: str) -> dict | None:
        raw = raw.strip()
        if raw.startswith("{"):
            try:
                return json.loads(raw)
            except ValueError:
                return None
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk:
                    try:
                        return json.loads(chunk)
                    except ValueError:
                        continue
        return None

    def rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        st, _, raw = self._post({"jsonrpc": "2.0", "id": self._id,
                                 "method": method, "params": params or {}})
        msg = self._parse(raw)
        if msg is None:
            raise McpError(f"{method}: HTTP {st}, unparseable body {raw[:300]!r}")
        if "error" in msg:
            raise McpError(f"{method}: {json.dumps(msg['error'])[:400]}")
        return msg.get("result", {})

    def connect(self) -> dict:
        st, hdr, raw = self._post({
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                       "clientInfo": {"name": "gamecreater", "version": "1"}}})
        msg = self._parse(raw)
        if msg is None or "error" in msg:
            raise McpError(f"initialize failed: HTTP {st} {raw[:300]!r}")
        self.sid = hdr.get("Mcp-Session-Id") or hdr.get("mcp-session-id")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.server_info = msg.get("result", {})
        return self.server_info

    # -- tools ------------------------------------------------------------
    def tools(self) -> list[dict]:
        return self.rpc("tools/list", {}).get("tools", [])

    def raw_call(self, name: str, arguments: dict) -> dict:
        return self.rpc("tools/call", {"name": name, "arguments": arguments})

    def text(self, name: str, arguments: dict) -> tuple[str, bool]:
        r = self.raw_call(name, arguments)
        out = [c.get("text", "") for c in r.get("content", [])
               if c.get("type") == "text"]
        return "\n".join(out), bool(r.get("isError"))

    def toolset_call(self, toolset: str, tool: str,
                     arguments: dict | None = None,
                     allow_reserved: bool = False) -> dict:
        if not allow_reserved and RESERVED_RE.search(tool):
            raise McpError(
                f"refusing to call {tool!r}: its name matches an act CLAUDE.md "
                f"reserves for per-act authorization. Ask, then pass "
                f"allow_reserved=True for that one call.")
        return self.raw_call("call_tool", {
            "toolset_name": toolset, "tool_name": tool,
            "arguments": arguments or {}})

    @staticmethod
    def image_bytes(result: dict) -> tuple[bytes | None, str | None]:
        """Extract an image from ANY of the three shapes this plugin uses.

        Measured 2026-08-14, all from the same toolset:
          1. a real MCP `image` content block            (rare)
          2. text block -> {"returnValue": {mimeType, data}}   CaptureEditorImage
          3. text block -> {"returnValue": {"image": {mimeType, data}}}
                                                              CaptureViewport
        Shape 3 cost a whole PIE cycle before it was noticed, because a
        handler that knows shapes 1-2 reports "no image payload" for a call
        that returned a perfectly good PNG. Walk the payload instead of
        assuming a depth.
        """
        def dig(node, depth=0):
            if depth > 4 or not isinstance(node, dict):
                return None
            if node.get("data"):
                return base64.b64decode(node["data"]), node.get("mimeType")
            for v in node.values():
                if isinstance(v, dict):
                    got = dig(v, depth + 1)
                    if got:
                        return got
            return None

        for c in result.get("content", []):
            if c.get("type") == "image" and c.get("data"):
                return base64.b64decode(c["data"]), c.get("mimeType")
            if c.get("type") == "text":
                try:
                    payload = json.loads(c["text"])
                except Exception:
                    continue
                got = dig(payload)
                if got:
                    return got
        return None, None


def probe(url: str | None = None) -> dict:
    """One-shot reachability probe used by engine_run.py mcp-check.

    Returns a dict; never raises. `speaks_mcp` is the only honest answer to
    "is MCP up", and it is strictly stronger than "the port is open"."""
    out = {"url": url or endpoint_from_config(), "speaks_mcp": False,
           "protocol": None, "tools": [], "error": None}
    try:
        m = Mcp(url)
        info = m.connect()
        out["protocol"] = info.get("protocolVersion")
        out["capabilities"] = sorted((info.get("capabilities") or {}).keys())
        out["session_id"] = m.sid
        out["tools"] = [t["name"] for t in m.tools()]
        out["speaks_mcp"] = True
    except Exception as e:                                       # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    return out


# --- cli -----------------------------------------------------------------

def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(prog="mcp_client")
    ap.add_argument("--url", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("handshake")
    sub.add_parser("toolsets")
    d = sub.add_parser("describe"); d.add_argument("toolset")
    c = sub.add_parser("call")
    c.add_argument("toolset"); c.add_argument("tool")
    c.add_argument("args", nargs="?", default="{}")
    c.add_argument("--allow-reserved", action="store_true")
    ce = sub.add_parser("capture-editor"); ce.add_argument("out", type=Path)
    ca = sub.add_parser("capture-asset")
    ca.add_argument("asset"); ca.add_argument("out", type=Path)
    a = ap.parse_args(argv[1:])

    if a.cmd == "handshake":
        p = probe(a.url)
        print(json.dumps(p, indent=2))
        return 0 if p["speaks_mcp"] else 1

    m = Mcp(a.url)
    try:
        m.connect()
    except McpError as e:
        print(f"NOT REACHABLE: {e}", file=sys.stderr)
        return 1

    if a.cmd == "toolsets":
        txt, err = m.text("list_toolsets", {})
        print(txt)
        print(f"\n{len(re.findall(r'^- ', txt, re.M))} toolsets", file=sys.stderr)
        return 1 if err else 0

    if a.cmd == "describe":
        txt, err = m.text("describe_toolset", {"toolset_name": a.toolset})
        print(txt)
        return 1 if err else 0

    if a.cmd == "call":
        try:
            r = m.toolset_call(a.toolset, a.tool, json.loads(a.args),
                               allow_reserved=a.allow_reserved)
        except McpError as e:
            print(f"REFUSED/FAILED: {e}", file=sys.stderr)
            return 2
        for c_ in r.get("content", []):
            print(c_.get("text", f"<{c_.get('type')}>"))
        return 1 if r.get("isError") else 0

    if a.cmd in ("capture-editor", "capture-asset"):
        if a.cmd == "capture-editor":
            r = m.toolset_call("EditorToolset.EditorAppToolset",
                               "CaptureEditorImage", {})
        else:
            r = m.toolset_call("EditorToolset.EditorAppToolset",
                               "CaptureAssetImage", {"assetPath": a.asset})
        if r.get("isError"):
            print("ERROR: " + " | ".join(
                c.get("text", "")[:300] for c in r.get("content", [])),
                file=sys.stderr)
            return 1
        data, mime = Mcp.image_bytes(r)
        if not data:
            print("no image payload in response", file=sys.stderr)
            return 1
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_bytes(data)
        print(f"{mime} -> {a.out}  ({len(data):,} bytes)")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
