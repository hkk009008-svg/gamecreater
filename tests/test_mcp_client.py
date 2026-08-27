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
import contextlib
import inspect
import io
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


class TestReadOnlyCallAllowlist(unittest.TestCase):
    """The nominally read-only helper exposes only its fixed capture calls."""

    def _client(self):
        m = mc.Mcp("http://127.0.0.1:1/mcp")
        m.sid = "fake"
        return m

    def test_every_unlisted_tool_is_refused_before_any_request(self):
        m = self._client()
        for name in ("DeleteAsset", "SetProperty", "WriteAsset",
                     "GetSelectedActors", "CookContent", "PackageProject"):
            with patch.object(mc.Mcp, "raw_call") as rc:
                with self.assertRaises(mc.McpError, msg=name) as caught:
                    m.toolset_call("Some.Toolset", name, {})
                self.assertIn("not one of", str(caught.exception))
                rc.assert_not_called()

    def test_only_fixed_capture_calls_pass_through(self):
        m = self._client()
        for name in ("CaptureEditorImage", "CaptureAssetImage"):
            with patch.object(mc.Mcp, "raw_call", return_value={"ok": 1}) as rc:
                m.toolset_call("EditorToolset.EditorAppToolset", name, {})
                rc.assert_called_once()

    def test_reserved_call_has_no_override(self):
        m = self._client()
        self.assertNotIn("allow_reserved",
                         inspect.signature(m.toolset_call).parameters)
        with patch.object(mc.Mcp, "raw_call") as rc:
            with self.assertRaises(TypeError):
                m.toolset_call("T", "DeleteAsset", {}, allow_reserved=True)
            rc.assert_not_called()


class TestFreshCaptureOutput(unittest.TestCase):
    def test_fresh_output_is_published(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "capture.png"
            mc.write_fresh(out, PNG)
            self.assertEqual(out.read_bytes(), PNG)

    def test_existing_output_is_refused_and_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "capture.png"
            original = b"existing evidence"
            out.write_bytes(original)
            with self.assertRaises(FileExistsError):
                mc.write_fresh(out, PNG)
            self.assertEqual(out.read_bytes(), original)

    def test_missing_parent_is_refused_without_creating_it(self):
        with tempfile.TemporaryDirectory() as t:
            parent = Path(t) / "missing"
            out = parent / "capture.png"
            with self.assertRaises(FileNotFoundError):
                mc.write_fresh(out, PNG)
            self.assertFalse(parent.exists())


class TestReadOnlyCliShape(unittest.TestCase):
    def test_help_only_advertises_fixed_read_only_operations(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as caught:
                mc.main(["mcp_client", "--help"])
        self.assertEqual(caught.exception.code, 0)
        help_text = stdout.getvalue()
        for command in ("handshake", "toolsets", "describe",
                        "capture-editor", "capture-asset"):
            self.assertIn(command, help_text)
        self.assertNotIn("allow-reserved", help_text)
        self.assertNotRegex(help_text, r"[,{]call[,}]")

    def test_generic_call_subcommand_is_rejected_before_connect(self):
        with patch.object(mc.Mcp, "connect") as connect:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    mc.main(["mcp_client", "call", "T", "DeleteAsset"])
        self.assertEqual(caught.exception.code, 2)
        connect.assert_not_called()


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

    def test_invalid_present_config_is_not_silently_replaced_by_default(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = Path(t) / ".mcp.json"
            cfg.write_text('{"mcpServers":{"unreal-mcp":{"url":"not a url"}}}',
                           encoding="utf-8")
            with self.assertRaises(mc.McpError):
                mc.endpoint_from_config(cfg)

    def test_endpoint_parts_handles_default_ports_and_rejects_credentials(self):
        self.assertEqual(mc.endpoint_parts("https://localhost/mcp"),
                         ("localhost", 443, "/mcp"))
        with self.assertRaises(mc.McpError):
            mc.endpoint_parts("http://user:secret@localhost:8000/mcp")
        with self.assertRaises(mc.McpError):
            mc.endpoint_parts("https://example.com/mcp")


class TestProbeNeverRaises(unittest.TestCase):
    """probe() feeds a diagnostic. A diagnostic that throws tells you
    nothing about the thing it was diagnosing."""

    def test_dead_endpoint_reports_not_speaking_mcp(self):
        p = mc.probe("http://127.0.0.1:1/mcp")
        self.assertFalse(p["speaks_mcp"])
        self.assertIsNotNone(p["error"])
        self.assertEqual(p["tools"], [])

    def test_non_loopback_endpoint_is_reported_not_raised(self):
        p = mc.probe("https://example.com/mcp")
        self.assertFalse(p["speaks_mcp"])
        self.assertIn("loopback", p["error"])

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
