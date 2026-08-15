"""Pin the MCP client's pure parts.

Every fixture is a shape observed against the LIVE Unreal editor on
2026-08-14, not an invention. The two that matter most are the ones that
cost round trips before they were understood:

  - images arrive JSON-WRAPPED IN A TEXT BLOCK, not as an MCP `image` block;
  - `inputSchema.required` is a LOWER BOUND -- CaptureViewport advertises no
    required params, documents `captureTransform` as optional, and then
    rejects `{}`.
"""

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import mcp_client as mc

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
B64 = base64.b64encode(PNG).decode()


class TestResponseParsing(unittest.TestCase):
    def test_plain_json_body(self):
        self.assertEqual(mc.Mcp._parse('{"jsonrpc":"2.0","result":{"a":1}}'),
                         {"jsonrpc": "2.0", "result": {"a": 1}})

    def test_sse_framed_body(self):
        raw = ("event: message\n"
               'data: {"jsonrpc":"2.0","result":{"a":2}}\n\n')
        self.assertEqual(mc.Mcp._parse(raw)["result"], {"a": 2})

    def test_unparseable_returns_none_not_an_exception(self):
        """A garbled body must degrade to 'could not tell', never to a
        crash that reads as 'server down'."""
        self.assertIsNone(mc.Mcp._parse("<html>502 Bad Gateway</html>"))
        self.assertIsNone(mc.Mcp._parse(""))


class TestImageExtraction(unittest.TestCase):
    def test_standard_mcp_image_block(self):
        r = {"content": [{"type": "image", "mimeType": "image/png", "data": B64}]}
        data, mime = mc.Mcp.image_bytes(r)
        self.assertEqual(data, PNG)
        self.assertEqual(mime, "image/png")

    def test_json_wrapped_in_a_text_block(self):
        """What CaptureEditorImage actually returns. A client that only
        handles type=='image' silently finds nothing and reports 'no image'
        for a call that succeeded."""
        r = {"content": [{"type": "text", "text": json.dumps(
            {"returnValue": {"mimeType": "image/png", "data": B64}})}]}
        data, mime = mc.Mcp.image_bytes(r)
        self.assertEqual(data, PNG)
        self.assertEqual(mime, "image/png")

    def test_text_block_without_an_image_is_not_mistaken_for_one(self):
        r = {"content": [{"type": "text",
                          "text": json.dumps({"returnValue": False})}]}
        self.assertEqual(mc.Mcp.image_bytes(r), (None, None))

    def test_non_json_text_block_does_not_raise(self):
        r = {"content": [{"type": "text", "text": "Asset not found: /Game/x"}]}
        self.assertEqual(mc.Mcp.image_bytes(r), (None, None))


class TestReservedActBackstop(unittest.TestCase):
    """CLAUDE.md reserves deletion, publishing and canonical writes for
    per-act authorization. Routing one through a toolset does not change
    that. This is a backstop, not a substitute for asking."""

    def _client(self):
        m = mc.Mcp("http://127.0.0.1:1/mcp")
        m.sid = "fake"
        return m

    def test_destructive_tool_names_are_refused_before_any_request(self):
        m = self._client()
        for name in ("DeleteAsset", "RemoveActor", "PublishPlugin",
                     "SetVisibility", "CookContent"):
            with patch.object(mc.Mcp, "raw_call") as rc:
                with self.assertRaises(mc.McpError, msg=name):
                    m.toolset_call("Some.Toolset", name, {})
                rc.assert_not_called()

    def test_read_only_tool_names_pass_through(self):
        """The quiet direction: a backstop that blocked everything would be
        removed within a day."""
        m = self._client()
        for name in ("GetSelectedActors", "CaptureAssetImage",
                     "ListTests", "DescribeToolset"):
            with patch.object(mc.Mcp, "raw_call", return_value={"ok": 1}) as rc:
                m.toolset_call("Some.Toolset", name, {})
                rc.assert_called_once()

    def test_reserved_can_be_called_explicitly_after_authorization(self):
        m = self._client()
        with patch.object(mc.Mcp, "raw_call", return_value={"ok": 1}) as rc:
            m.toolset_call("T", "DeleteAsset", {}, allow_reserved=True)
            rc.assert_called_once()


class TestEndpointConfig(unittest.TestCase):
    def test_url_is_read_from_mcp_json(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = Path(t) / ".mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {"unreal-mcp": {
                "url": "http://127.0.0.1:9999/other"}}}), encoding="utf-8")
            self.assertEqual(mc.endpoint_from_config(cfg),
                             "http://127.0.0.1:9999/other")

    def test_missing_config_falls_back_to_the_plugin_default(self):
        self.assertEqual(mc.endpoint_from_config(Path("Z:/nope.json")),
                         mc.DEFAULT_URL)


class TestProbeNeverRaises(unittest.TestCase):
    """probe() feeds a diagnostic. A diagnostic that throws tells you
    nothing about the thing it was diagnosing."""

    def test_dead_endpoint_reports_not_speaking_mcp(self):
        p = mc.probe("http://127.0.0.1:1/mcp")
        self.assertFalse(p["speaks_mcp"])
        self.assertIsNotNone(p["error"])
        self.assertEqual(p["tools"], [])

    def test_garbage_response_is_not_a_pass(self):
        """Something answering HTTP on the port is not an MCP server."""
        with patch.object(mc.Mcp, "_post",
                          return_value=(200, {}, "<html>hello</html>")):
            p = mc.probe("http://127.0.0.1:8000/mcp")
        self.assertFalse(p["speaks_mcp"])

    def test_successful_handshake_reports_protocol_and_tools(self):
        """Known-positive control: without it, a probe hardwired to False
        would pass both tests above."""
        init = json.dumps({"jsonrpc": "2.0", "id": 0, "result": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}, "resources": {}}}})
        listed = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
            "tools": [{"name": "list_toolsets"}, {"name": "call_tool"}]}})
        seq = [(200, {"Mcp-Session-Id": "abc"}, init), (200, {}, ""),
               (200, {}, listed)]
        with patch.object(mc.Mcp, "_post", side_effect=seq):
            p = mc.probe("http://127.0.0.1:8000/mcp")
        self.assertTrue(p["speaks_mcp"])
        self.assertEqual(p["protocol"], "2025-06-18")
        self.assertEqual(p["session_id"], "abc")
        self.assertEqual(p["tools"], ["list_toolsets", "call_tool"])


if __name__ == "__main__":
    unittest.main()
