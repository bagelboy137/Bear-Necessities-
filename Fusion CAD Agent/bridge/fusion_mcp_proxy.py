#!/usr/bin/env python3
"""fusion_mcp_proxy.py - a stdio MCP server that fronts Fusion's local one.

Claude Code (or any MCP client) launches this; it forwards to the MCP server
built into desktop Fusion and adds what this project learned the hard way:

1. The port moves. Fusion documents 27182 and has come back on 27180 after a
   crash-relaunch. A client pinned to one URL reports "is Fusion running?"
   while it is. This finds the port through fusion_port.discover() whenever it
   (re)connects.
2. A Fusion relaunch forgets the MCP session. When a call is refused before it
   could run - nothing listening, or a session the server no longer knows - the
   proxy reconnects and sends it once more. A call Fusion accepted and never
   answered is never resent: it may have run.
3. Some scripts hang Fusion until a human clicks. Modal dialogs and closing a
   document (its save prompt is modal) block the API for good, so they are
   refused here with a message the model can act on, before Fusion sees them.
4. Every execute is logged - script, arguments, outcome - so a change to a
   design has provenance, the way every other artefact in this project does.
5. Two tools of its own: bn_fusion_status (is Fusion there, and how to fix it
   if not) and bn_snapshot (a read-only inventory to diff before and after an
   edit; see fusion_snapshot.py).

Everything else - tool list, arguments, images, structured results - passes
through untouched, so tools Autodesk adds later appear without a change here.

Standard library only, and Python 3.8+ syntax: on a Mac this runs under
whatever `python3` Claude finds, not the CadQuery venv.

    python3 fusion_mcp_proxy.py            # speak MCP on stdin/stdout
    python3 fusion_mcp_proxy.py --status   # one-shot reachability report

Environment:
    BN_FUSION_MCP_URL   force a URL instead of discovering one
    BN_FUSION_GUARDS    "off" lets refused patterns through (logged)
    BN_FUSION_LOG_DIR   where the execute log goes (default bridge/logs/mcp)
    BN_FUSION_TIMEOUT   seconds to wait on Fusion per call (default 300)
"""

import ast
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fusion_snapshot  # noqa: E402
from fusion_mcp import (FusionHTTPError, FusionMCP, FusionNoReply,  # noqa: E402
                        FusionUnreachable)

NAME = "bear-necessities-fusion"
VERSION = "1.0"
SUPPORTED_PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
EXECUTE = "fusion_mcp_execute"
# Calls that cannot change a design, so the log skips them (screenshots are big).
READ_ONLY_TOOLS = ("fusion_mcp_read",)

INSTRUCTIONS = """\
Live desktop Autodesk Fusion, through the Bear Necessities proxy.
- Load the fusion-cad skill before editing a design; it holds the procedure.
- Start with bn_snapshot; repeat it after every write and compare the numbers
  with what you predicted. Call bn_fusion_status if tools seem missing.
- Fusion's API lengths are centimetres (1 in = 2.54); prefer
  ValueInput.createByString("18 in") so the unit is explicit.
- Scripts define run(_context: str) and report with print().
- Modal dialogs and closing documents are refused: both block Fusion's API
  until a human clicks.
- A write that timed out may still have run: snapshot before retrying."""

EXECUTE_NOTE = (
    "[Bear Necessities proxy] Scripts must define run(_context: str) and report "
    "with print(). API lengths are CENTIMETRES (1 in = 2.54). Pass "
    "object.readOnly=true for inspection. Modal dialogs and closing documents are "
    "refused because they block Fusion's API. One small script per step; check "
    "the result with bn_snapshot.\n\n")

LOCAL_TOOLS = [
    {
        "name": "bn_fusion_status",
        "description": (
            "Report whether desktop Fusion's MCP server is reachable, at which URL, "
            "which tools it offers, and exactly what to do if it is not reachable. "
            "Reconnects if Fusion has come up since the last call."),
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True, "title": "Fusion connection status"},
    },
    {
        "name": "bn_snapshot",
        "description": (
            "Read-only inventory of the active Fusion design: document id/version, "
            "every body's bounding box and volume in assembly coordinates, "
            "occurrences, timeline health, user parameters and joints. Run it before "
            "an edit and again after, and compare against the change you predicted."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "units": {"type": "string", "enum": list(fusion_snapshot.UNITS),
                          "default": "in",
                          "description": "Units for lengths and volumes."},
                "detail": {"type": "string", "enum": ["summary", "full"],
                           "default": "full",
                           "description": "summary skips the per-body and "
                                          "per-occurrence lists."},
            },
        },
        "annotations": {"readOnlyHint": True, "title": "Fusion design snapshot"},
    },
]

NOT_REACHABLE_HELP = """\
Desktop Fusion's MCP server is not reachable from here.

On the Mac:
  1. Open Fusion and open (or create) a design.
  2. Preferences > General > API > tick "Fusion MCP Server".
  3. Call bn_fusion_status again - the port is discovered, so a moved port is fine.
If it still fails, run `python3 "Fusion CAD Agent/bridge/fusion_port.py"` in a
terminal to see which URL discovery settles on."""

REMOTE_HELP = """\
This is a cloud session: desktop Fusion runs on Conor's Mac and its MCP server
listens only on that machine's 127.0.0.1, so it can never be reached from here.
For Fusion from a cloud session, use Autodesk's Fusion Compute MCP server
(headless Fusion in Autodesk's cloud): add
https://developer.api.autodesk.com/da/v3/mcp/fusion as a custom connector at
claude.ai/customize/connectors, sign in with Autodesk, then start a new session."""


# -- guards ---------------------------------------------------------------

# Calls that open a window and wait for a click. Fusion's API stalls until a
# human answers, so an unattended agent wedges the whole session.
MODAL_CALLS = ("messageBox", "inputBox", "createFileDialog", "createFolderDialog")


def _names_in(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            yield sub.id
        elif isinstance(sub, ast.Attribute):
            yield sub.attr


def script_refusals(src):
    """Reasons a script must not reach Fusion. [] means send it.

    Parsed with this interpreter, which may be older than Fusion's. A script
    this Python cannot parse is not refused for that - Fusion is the judge of
    its own syntax - and falls back to pattern checks instead.
    """
    if not isinstance(src, str) or not src.strip():
        return ["The script is empty. Send Python that defines run(_context: str)."]
    found = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        tree = None
    if tree is not None:
        has_run = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and n.name == "run" for n in tree.body)
        modal, closes = set(), False
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr in MODAL_CALLS:
                modal.add(node.func.attr)
            elif node.func.attr == "close" and any(
                    "doc" in name.lower() for name in _names_in(node.func.value)):
                closes = True
    else:
        has_run = re.search(r"^def\s+run\s*\(", src, re.M) is not None
        modal = {m for m in MODAL_CALLS if re.search(r"\.%s\s*\(" % m, src)}
        closes = re.search(r"(?i)doc[\w.\[\]()]*\.close\s*\(", src) is not None
    if not has_run:
        found.append("No module-level run() function. Fusion's entry point is "
                     "`def run(_context: str):` - put the work inside it.")
    for name in sorted(modal):
        found.append("`%s(...)` opens a modal dialog, which blocks Fusion's API until "
                     "a human clicks it. Use print() - its output is returned to you."
                     % name)
    if closes:
        found.append("Closing a document is refused: its save prompt is modal and "
                     "blocks Fusion's API. Leave documents open; if one must be "
                     "closed, ask the user to close it.")
    return found


def execute_refusals(arguments):
    """Refusals for a fusion_mcp_execute call, whatever its featureType."""
    if not isinstance(arguments, dict):
        return []
    kind = arguments.get("featureType")
    obj = arguments.get("object") or {}
    if not isinstance(obj, dict):
        return []
    if kind == "document" and str(obj.get("operation", "")).lower() == "close":
        return ["Closing a document is refused: its save prompt is modal and blocks "
                "Fusion's API. Save it instead (operation 'save'), and ask the user "
                "if it really has to be closed."]
    if kind == "script":
        return script_refusals(obj.get("script"))
    return []


def _text_result(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


LOG_TEXT_LIMIT = 4000


def _loggable(result):
    """A copy safe to log: images reduced to their size, long text clipped."""
    if not isinstance(result, dict):
        return result
    out = dict(result)
    blocks = []
    for block in result.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "image":
            block = {"type": "image", "mimeType": block.get("mimeType"),
                     "bytes_base64": len(block.get("data", "") or "")}
        elif isinstance(block, dict) and len(block.get("text", "") or "") > LOG_TEXT_LIMIT:
            block = dict(block, text=block["text"][:LOG_TEXT_LIMIT] + " [clipped]")
        blocks.append(block)
    out["content"] = blocks
    out.pop("structuredContent", None)
    return out


# -- the proxy ------------------------------------------------------------

class Proxy:
    def __init__(self, emit, env=None, discover=None, client_factory=None):
        self.emit = emit                      # writes one JSON-RPC message
        self.env = os.environ if env is None else env
        self._discover = discover or _default_discover
        self._client_factory = client_factory or FusionMCP
        try:
            self.timeout = float(self.env.get("BN_FUSION_TIMEOUT", "300"))
        except ValueError:
            self.timeout = 300.0
        self.guards = self.env.get("BN_FUSION_GUARDS", "on").lower() != "off"
        self.log_dir = self.env.get("BN_FUSION_LOG_DIR") or os.path.join(
            HERE, "logs", "mcp")
        self.client = None
        self.url = None
        self.last_error = None
        self.reachable = None                 # None until first probed
        self.upstream_tools = []

    # upstream connection ------------------------------------------------

    def _connect(self):
        """Return a live client, connecting (and rediscovering) if needed."""
        if self.client is not None:
            return self.client
        self.url = self._discover(self.env)
        client = self._client_factory(self.url, timeout=self.timeout)
        try:
            client.connect()
        except Exception as e:
            self.last_error = str(e)
            self._set_reachable(False)
            raise
        self.client = client
        self.last_error = None
        self._set_reachable(True)
        return client

    def _drop(self):
        self.client = None

    def _set_reachable(self, value):
        changed = self.reachable is not None and value != self.reachable
        self.reachable = value
        if changed:
            # The tool list depends on this, so tell the client to refetch it.
            self.emit({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"})

    def _upstream(self, method, *args):
        """Call a client method, reconnecting once when that is provably safe.

        Safe means the request never ran: nothing was listening, or the server
        rejected the session before dispatching. A request that timed out or
        lost its connection mid-reply is not retried - Fusion may have run it.
        """
        for attempt in (1, 2):
            client = self._connect()
            try:
                return getattr(client, method)(*args)
            except FusionUnreachable as e:
                self._drop()
                self.last_error = str(e)
                if attempt == 2:
                    self._set_reachable(False)
                    raise
            except FusionHTTPError as e:
                self._drop()
                self.last_error = str(e)
                if attempt == 2 or not (e.code == 404 or "session" in e.body.lower()):
                    raise

    def _fetch_tools(self):
        try:
            tools = self._upstream("tools")
        except Exception as e:
            self.last_error = str(e)
            self.upstream_tools = []
            return []
        self.upstream_tools = tools
        return tools

    # MCP methods ---------------------------------------------------------

    def handle(self, msg):
        """One JSON-RPC message in; the reply (or None for a notification)."""
        if not isinstance(msg, dict):
            return _error(None, -32600, "Invalid request")
        method, mid = msg.get("method"), msg.get("id")
        params = msg.get("params") or {}
        if mid is None or method is None:
            # A notification, or a response to a request: neither gets a reply.
            return None
        try:
            if method == "initialize":
                return _reply(mid, self._initialize(params))
            if method == "ping":
                return _reply(mid, {})
            if method == "tools/list":
                return _reply(mid, {"tools": self._tools_list()})
            if method == "tools/call":
                return _reply(mid, self._tools_call(params))
        except Exception as e:                # never let one call kill the server
            return _error(mid, -32603, "%s: %s" % (type(e).__name__, e))
        return _error(mid, -32601, "Method not found: %s" % method)

    def _initialize(self, params):
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_PROTOCOLS else "2025-06-18"
        return {"protocolVersion": version,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": NAME, "version": VERSION},
                "instructions": INSTRUCTIONS}

    def _tools_list(self):
        tools = []
        for tool in self._fetch_tools():
            tool = dict(tool)
            if tool.get("name") == EXECUTE:
                tool["description"] = EXECUTE_NOTE + (tool.get("description") or "")
            if tool.get("name") not in {t["name"] for t in LOCAL_TOOLS}:
                tools.append(tool)
        return tools + [dict(t) for t in LOCAL_TOOLS]

    def _tools_call(self, params):
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "bn_fusion_status":
            return self._status()
        if name == "bn_snapshot":
            return self._snapshot(args)
        return self._forward(name, args)

    def _forward(self, name, args, log_args=None):
        """Send one tool call to Fusion. `log_args` replaces the arguments in
        the log, for calls whose arguments are this proxy's own boilerplate."""
        logged = args if log_args is None else log_args
        if name == EXECUTE:
            refusals = execute_refusals(args)
            if refusals and self.guards:
                self._log(name, logged, "refused", {"refusals": refusals})
                return _text_result(
                    "Not sent to Fusion:\n" + "\n".join(
                        "%d. %s" % (i, r) for i, r in enumerate(refusals, 1)), True)
        started = time.time()
        try:
            result = self._upstream("call_raw", name, args)
        except FusionNoReply as e:
            self._log(name, logged, "no-reply", {"error": str(e)}, started)
            return _text_result(
                "%s\nFusion may still be running this, or may have finished it. Do "
                "not resend a write: call bn_snapshot first and check whether it "
                "took effect." % e, True)
        except FusionUnreachable as e:
            self._log(name, logged, "unreachable", {"error": str(e)}, started)
            return _text_result("%s\n\n%s" % (e, self._help()), True)
        except Exception as e:
            self._log(name, logged, "error", {"error": str(e)}, started)
            return _text_result("Fusion call failed: %s" % e, True)
        if name not in READ_ONLY_TOOLS:
            # Undo, redo and whatever Autodesk adds next can change a design too.
            self._log(name, logged, "error" if result.get("isError") else "ok",
                      _loggable(result), started)
        return result

    def _status(self):
        report = self.status_report()
        # Unreachable is an answer, not a failed call: the report says so.
        return _text_result(json.dumps(report, indent=2))

    def status_report(self):
        if self.client is None:
            try:
                self._connect()
            except Exception:
                pass
        if self.client is not None:
            tools = self._fetch_tools()
        else:
            tools = []
        report = {
            "reachable": self.client is not None,
            "url": self.url,
            "server": getattr(self.client, "server_info", None) if self.client else None,
            "fusion_tools": [t.get("name") for t in tools],
            "guards": "on" if self.guards else "OFF (BN_FUSION_GUARDS=off)",
            "execute_log": self.log_dir,
            "cloud_session": self._remote(),
        }
        if self.client is None:
            report["last_error"] = self.last_error
            report["fix"] = self._help()
        return report

    def _snapshot(self, args):
        try:
            src = fusion_snapshot.script(args.get("units", "in"),
                                         args.get("detail", "full"))
        except ValueError as e:
            return _text_result(str(e), True)
        result = self._forward(EXECUTE, {"featureType": "script",
                                         "object": {"script": src, "readOnly": True}},
                               log_args={"bn_snapshot": args})
        if result.get("isError"):
            return result
        try:
            snap = fusion_snapshot.parse(result)
        except ValueError as e:
            snap, problem = None, "unparseable snapshot JSON: %s" % e
        else:
            problem = "the snapshot script ran but printed no BN_SNAPSHOT line"
        if snap is None:
            texts = [b.get("text", "") for b in result.get("content", [])
                     if isinstance(b, dict) and b.get("type") == "text"]
            return _text_result("%s. Fusion returned:\n%s"
                                % (problem, "\n".join(texts)[:4000]), True)
        return {"content": [{"type": "text",
                             "text": json.dumps(snap, separators=(",", ":"))}],
                "structuredContent": snap, "isError": False}

    # helpers -------------------------------------------------------------

    def _remote(self):
        return self.env.get("CLAUDE_CODE_REMOTE", "").lower() == "true"

    def _help(self):
        return REMOTE_HELP if self._remote() else NOT_REACHABLE_HELP

    def _log(self, tool, args, outcome, detail, started=None):
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "tool": tool,
                  "url": self.url, "outcome": outcome, "arguments": args,
                  "detail": detail}
        if started is not None:
            record["seconds"] = round(time.time() - started, 2)
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            path = os.path.join(self.log_dir,
                                "fusion-mcp-%s.jsonl" % time.strftime("%Y%m%d"))
            with open(path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except OSError as e:
            # A log that cannot be written must not stop the design work.
            sys.stderr.write("fusion proxy: could not write log: %s\n" % e)


def _default_discover(env):
    override = env.get("BN_FUSION_MCP_URL")
    if override:
        return override
    from fusion_port import discover
    return discover(configured="auto")


def _reply(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _error(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def serve(stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout

    def emit(message):
        stdout.write(json.dumps(message) + "\n")
        stdout.flush()

    proxy = Proxy(emit)
    while True:
        line = stdin.readline()
        if not line:
            break                             # client closed stdin: exit
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            emit(_error(None, -32700, "Parse error"))
            continue
        for item in (msg if isinstance(msg, list) else [msg]):
            reply = proxy.handle(item)
            if reply is not None:
                emit(reply)
    return 0


def main(argv):
    if len(argv) > 1 and argv[1] == "--status":
        report = Proxy(lambda _m: None).status_report()
        print(json.dumps(report, indent=2))
        return 0 if report["reachable"] else 1
    return serve()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
