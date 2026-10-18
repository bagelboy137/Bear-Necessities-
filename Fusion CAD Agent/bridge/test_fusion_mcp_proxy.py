#!/usr/bin/env python3
"""Tests for the Fusion MCP proxy, against a fake Fusion. No Fusion, no network.

The fake speaks the parts of Fusion's server this project has had to handle:
the session id in a response header, the mandatory notifications/initialized,
stdout wrapped in a {"message", "success"} envelope, optional SSE framing, and a
relaunch that forgets every session. What it cannot stand in for is Fusion's
API itself - a passing run here says the proxy is right, not that a script is.

Same counting runner as bncad/tests/test_bncad.py, and the same rule: every
guard is shown refusing something and letting the legitimate case through.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import fusion_mcp                                   # noqa: E402
import fusion_mcp_proxy as P                        # noqa: E402
import fusion_snapshot                              # noqa: E402

PASSED, FAILED = [], []


def check(name):
    def deco(fn):
        try:
            fn()
        except AssertionError as e:
            FAILED.append((name, "assertion: %s" % e))
        except Exception as e:
            FAILED.append((name, "%s: %s" % (type(e).__name__, e)))
        else:
            PASSED.append(name)
        return fn
    return deco


# -- a fake Fusion --------------------------------------------------------

UPSTREAM_TOOLS = [
    {"name": "fusion_mcp_read", "description": "Read things.",
     "inputSchema": {"type": "object"}},
    {"name": "fusion_mcp_execute", "description": "Run a script.",
     "inputSchema": {"type": "object"}},
    {"name": "bn_snapshot", "description": "A colliding name the proxy must drop.",
     "inputSchema": {"type": "object"}},
]
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"


class FakeFusion:
    def __init__(self, sse=False):
        self.sse = sse
        self.sessions, self.ready = set(), set()
        self.calls = []                 # (tool, arguments) for every tools/call
        self.execute_delay = 0.0
        self.snapshot = {"units": "in", "bodies": {"count": 3}}
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                msg = json.loads(body)
                fake.handle(self, msg)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/mcp" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def forget_sessions(self):          # what a relaunch does
        self.sessions.clear()
        self.ready.clear()

    def executes(self):
        return [a for t, a in self.calls if t == "fusion_mcp_execute"]

    def _send(self, h, status, payload=None, headers=None, text=None):
        if text is not None:
            data, ctype = text.encode(), "text/plain"
        elif payload is None:
            data, ctype = b"", "application/json"
        elif self.sse:
            noise = {"jsonrpc": "2.0", "method": "notifications/message",
                     "params": {"level": "info", "data": "working"}}
            data = ("event: message\ndata: %s\n\nevent: message\ndata: %s\n\n"
                    % (json.dumps(noise), json.dumps(payload))).encode()
            ctype = "text/event-stream"
        else:
            data, ctype = json.dumps(payload).encode(), "application/json"
        h.send_response(status)
        h.send_header("Content-Type", ctype)
        h.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            h.send_header(k, v)
        h.end_headers()
        try:
            h.wfile.write(data)
        except BrokenPipeError:
            pass                        # the client gave up first: the no-reply test

    def handle(self, h, msg):
        method, mid = msg.get("method"), msg.get("id")
        sid = h.headers.get("MCP-Session-Id")
        if method == "initialize":
            new = "s%d" % (len(self.sessions) + 1 + int(time.time() * 1000) % 100000)
            self.sessions.add(new)
            self._send(h, 200, {"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": msg["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-fusion", "version": "0"}}},
                headers={"MCP-Session-Id": new})
            return
        if sid not in self.sessions:
            self._send(h, 404, text="Session not found")
            return
        if method == "notifications/initialized":
            self.ready.add(sid)
            self._send(h, 202)
            return
        if sid not in self.ready:
            self._send(h, 400, text="Session not initialized")
            return
        if method == "tools/list":
            self._send(h, 200, {"jsonrpc": "2.0", "id": mid,
                                "result": {"tools": UPSTREAM_TOOLS}})
            return
        if method == "tools/call":
            name, args = msg["params"]["name"], msg["params"].get("arguments", {})
            self.calls.append((name, args))
            self._send(h, 200, {"jsonrpc": "2.0", "id": mid,
                                "result": self._result(name, args)})
            return
        self._send(h, 200, {"jsonrpc": "2.0", "id": mid,
                            "error": {"code": -32601, "message": "no"}})

    def _result(self, name, args):
        if name == "fusion_mcp_read" and args.get("queryType") == "screenshot":
            return {"content": [{"type": "image", "mimeType": "image/png", "data": PNG}]}
        if name == "fusion_mcp_execute":
            if self.execute_delay:
                time.sleep(self.execute_delay)
            script = (args.get("object") or {}).get("script", "")
            out = ("BN_SNAPSHOT %s\n" % json.dumps(self.snapshot)
                   if "BN_SNAPSHOT" in script else "ran\n")
            return {"content": [{"type": "text", "text": json.dumps(
                {"message": out, "success": True})}]}
        return {"content": [{"type": "text", "text": "ok"}]}


DEAD_URL = "http://127.0.0.1:9/mcp"     # discard port: nothing listens there
GOOD = "def run(_context: str):\n    print('hi')\n"


def make_proxy(urls, **env):
    """A proxy whose discovery returns `urls` in turn (the last one repeats)."""
    seq = list(urls) if isinstance(urls, (list, tuple)) else [urls]
    sent = []
    log_dir = tempfile.mkdtemp(prefix="bn-proxy-log-")
    base = {"BN_FUSION_LOG_DIR": log_dir, "BN_FUSION_TIMEOUT": "5"}
    base.update(env)

    def discover(_env):
        return seq.pop(0) if len(seq) > 1 else seq[0]
    proxy = P.Proxy(sent.append, env=base, discover=discover)
    return proxy, sent, log_dir


def call(proxy, name, arguments=None, mid=1):
    reply = proxy.handle({"jsonrpc": "2.0", "id": mid, "method": "tools/call",
                          "params": {"name": name, "arguments": arguments or {}}})
    assert "result" in reply, reply
    return reply["result"]


def text(result):
    return "\n".join(b.get("text", "") for b in result.get("content", [])
                     if b.get("type") == "text")


def tool_names(proxy):
    reply = proxy.handle({"jsonrpc": "2.0", "id": 9, "method": "tools/list"})
    return [t["name"] for t in reply["result"]["tools"]]


def execute(script):
    return {"featureType": "script", "object": {"script": script}}


def log_records(log_dir):
    rows = []
    for f in sorted(pathlib.Path(log_dir).glob("*.jsonl")):
        rows += [json.loads(line) for line in f.read_text().splitlines()]
    return rows


# -- the client the proxy is built on -------------------------------------

@check("fusion_mcp: nothing listening is FusionUnreachable, still a RuntimeError")
def _t():
    c = fusion_mcp.FusionMCP(DEAD_URL, timeout=2)
    try:
        c.connect()
    except fusion_mcp.FusionUnreachable as e:
        assert isinstance(e, RuntimeError), "existing callers catch RuntimeError"
        assert "Is Fusion running" in str(e)
    else:
        raise AssertionError("connected to a dead port")


@check("fusion_mcp: a forgotten session is FusionHTTPError with its status code")
def _t():
    fake = FakeFusion()
    try:
        c = fusion_mcp.FusionMCP(fake.url, timeout=5)
        c.connect()
        fake.forget_sessions()
        try:
            c.tools()
        except fusion_mcp.FusionHTTPError as e:
            assert e.code == 404 and "Session" in e.body, (e.code, e.body)
        else:
            raise AssertionError("a forgotten session went unnoticed")
    finally:
        fake.stop()


@check("fusion_mcp: an SSE reply is matched by id, not taken from the first event")
def _t():
    fake = FakeFusion(sse=True)
    try:
        c = fusion_mcp.FusionMCP(fake.url, timeout=5)
        c.connect()
        assert [t["name"] for t in c.tools()][:2] == ["fusion_mcp_read",
                                                      "fusion_mcp_execute"]
        out, err = c.run_script(GOOD)
        assert not err and "ran" in out, out
    finally:
        fake.stop()


@check("fusion_mcp: call_raw keeps image blocks that call() would flatten away")
def _t():
    fake = FakeFusion()
    try:
        c = fusion_mcp.FusionMCP(fake.url, timeout=5)
        c.connect()
        raw = c.call_raw("fusion_mcp_read", {"queryType": "screenshot"})
        assert raw["content"][0]["type"] == "image"
        assert raw["content"][0]["data"] == PNG
    finally:
        fake.stop()


# -- protocol --------------------------------------------------------------

@check("proxy: initialize needs no Fusion and advertises tool-list changes")
def _t():
    proxy, _, _ = make_proxy(DEAD_URL)
    r = proxy.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                      "params": {"protocolVersion": "2025-06-18"}})["result"]
    assert r["protocolVersion"] == "2025-06-18"
    assert r["capabilities"]["tools"]["listChanged"] is True
    assert "centimetres" in r["instructions"]
    assert proxy.reachable is None, "initialize must not block on probing Fusion"


@check("proxy: an unknown protocol version gets one the proxy speaks")
def _t():
    proxy, _, _ = make_proxy(DEAD_URL)
    r = proxy.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                      "params": {"protocolVersion": "1999-01-01"}})["result"]
    assert r["protocolVersion"] in P.SUPPORTED_PROTOCOLS


@check("proxy: notifications and responses get no reply; unknown methods get -32601")
def _t():
    proxy, _, _ = make_proxy(DEAD_URL)
    assert proxy.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert proxy.handle({"jsonrpc": "2.0", "id": 7, "result": {}}) is None, \
        "a response from the client must not be answered with an error"
    r = proxy.handle({"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
    assert r["error"]["code"] == -32601


# -- with Fusion closed ----------------------------------------------------

@check("proxy: with Fusion closed, only its own tools are listed")
def _t():
    proxy, _, _ = make_proxy(DEAD_URL)
    assert tool_names(proxy) == ["bn_fusion_status", "bn_snapshot"]
    assert proxy.reachable is False


@check("proxy: bn_fusion_status explains the fix, for the Mac and for the cloud")
def _t():
    proxy, _, _ = make_proxy(DEAD_URL)
    report = json.loads(text(call(proxy, "bn_fusion_status")))
    assert report["reachable"] is False and "Preferences > General > API" in report["fix"]
    remote, _, _ = make_proxy(DEAD_URL, CLAUDE_CODE_REMOTE="true")
    report = json.loads(text(call(remote, "bn_fusion_status")))
    assert report["cloud_session"] is True
    assert "da/v3/mcp/fusion" in report["fix"], "cloud sessions are pointed at Fusion Compute"


@check("proxy: a call with Fusion closed is an error result, not a crash")
def _t():
    proxy, _, _ = make_proxy(DEAD_URL)
    r = call(proxy, "fusion_mcp_execute", execute(GOOD))
    assert r["isError"] and "Cannot reach" in text(r)


# -- with Fusion open -------------------------------------------------------

@check("proxy: Fusion's tools pass through, the execute note is prepended")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, _ = make_proxy(fake.url)
        reply = proxy.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = {t["name"]: t for t in reply["result"]["tools"]}
        assert set(tools) == {"fusion_mcp_read", "fusion_mcp_execute",
                              "bn_fusion_status", "bn_snapshot"}
        desc = tools["fusion_mcp_execute"]["description"]
        assert desc.startswith("[Bear Necessities proxy]") and desc.endswith("Run a script.")
        assert tools["fusion_mcp_read"]["description"] == "Read things."
        assert tools["bn_snapshot"]["description"] != "A colliding name the proxy must drop."
    finally:
        fake.stop()


@check("proxy: a good script reaches Fusion once and its result comes back intact")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, log_dir = make_proxy(fake.url)
        r = call(proxy, "fusion_mcp_execute", execute(GOOD))
        assert not r.get("isError") and "ran" in text(r), r
        assert len(fake.executes()) == 1
        rows = log_records(log_dir)
        assert rows[-1]["outcome"] == "ok"
        assert rows[-1]["arguments"]["object"]["script"] == GOOD, "the log holds the script"
    finally:
        fake.stop()


@check("proxy: any non-read Fusion tool is logged, e.g. undo")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, log_dir = make_proxy(fake.url)
        r = call(proxy, "fusion_mcp_update", {"operation": "undo"})
        assert not r.get("isError")
        rows = log_records(log_dir)
        assert rows and rows[-1]["tool"] == "fusion_mcp_update", rows
    finally:
        fake.stop()


@check("proxy: screenshots pass through as images, and are never written to the log")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, log_dir = make_proxy(fake.url)
        r = call(proxy, "fusion_mcp_read", {"queryType": "screenshot",
                                            "direction": "iso-top-right"})
        assert r["content"][0] == {"type": "image", "mimeType": "image/png", "data": PNG}
        assert PNG not in json.dumps(log_records(log_dir))
    finally:
        fake.stop()


# -- guards: each refuses, and nothing reaches Fusion -------------------------

REFUSED = {
    "modal message box": "def run(_context: str):\n"
                         "    import adsk.core\n"
                         "    adsk.core.Application.get().userInterface.messageBox('x')\n",
    "file dialog": "def run(_context: str):\n    ui.createFileDialog()\n",
    "closing a document": "def run(_context: str):\n"
                          "    app.activeDocument.close(False)\n",
    "closing a document by index": "def run(_context: str):\n"
                                   "    app.documents.item(0).close(True)\n",
    "no run() entry point": "print('hello')\n",
    "an empty script": "   \n",
}

for _label, _src in REFUSED.items():
    @check("guard refuses %s without sending it" % _label)
    def _t(src=_src):
        fake = FakeFusion()
        try:
            proxy, _, log_dir = make_proxy(fake.url)
            r = call(proxy, "fusion_mcp_execute", execute(src))
            assert r["isError"] and text(r).startswith("Not sent to Fusion"), r
            assert fake.executes() == [], "a refused script reached Fusion"
            assert log_records(log_dir)[-1]["outcome"] == "refused"
        finally:
            fake.stop()


@check("guard refuses the document-close operation itself")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, _ = make_proxy(fake.url)
        r = call(proxy, "fusion_mcp_execute",
                 {"featureType": "document", "object": {"operation": "Close"}})
        assert r["isError"] and "save prompt is modal" in text(r)
        assert fake.executes() == []
        r = call(proxy, "fusion_mcp_execute",
                 {"featureType": "document",
                  "object": {"operation": "save", "userMessageSummary": "x"}})
        assert not r.get("isError") and len(fake.executes()) == 1, "save must pass"
    finally:
        fake.stop()


@check("guard lets through look-alikes: file.close(), print('messageBox')")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, _ = make_proxy(fake.url)
        src = ("def run(_context: str):\n"
               "    f = open('/tmp/x.txt', 'w')\n    f.close()\n"
               "    print('never call messageBox here')\n")
        r = call(proxy, "fusion_mcp_execute", execute(src))
        assert not r.get("isError"), text(r)
        assert len(fake.executes()) == 1
    finally:
        fake.stop()


@check("guard leaves syntax to Fusion: an unparseable script is still sent")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, _ = make_proxy(fake.url)
        r = call(proxy, "fusion_mcp_execute",
                 execute("def run(_context: str):\n    x = (\n"))
        assert not r.get("isError") and len(fake.executes()) == 1
        r = call(proxy, "fusion_mcp_execute",
                 execute("def run(_context: str):\n    ui.messageBox(\n"))
        assert r["isError"], "the pattern fallback still catches a modal call"
        assert len(fake.executes()) == 1
    finally:
        fake.stop()


@check("BN_FUSION_GUARDS=off sends a refused script, and the log says so")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, log_dir = make_proxy(fake.url, BN_FUSION_GUARDS="off")
        r = call(proxy, "fusion_mcp_execute", execute(REFUSED["modal message box"]))
        assert not r.get("isError") and len(fake.executes()) == 1
        report = json.loads(text(call(proxy, "bn_fusion_status")))
        assert report["guards"].startswith("OFF")
    finally:
        fake.stop()


# -- reconnecting: only when nothing can have run ------------------------------

@check("a relaunch that forgets the session is retried once, and runs once")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, _ = make_proxy(fake.url)
        call(proxy, "fusion_mcp_execute", execute(GOOD))
        fake.forget_sessions()
        r = call(proxy, "fusion_mcp_execute", execute(GOOD))
        assert not r.get("isError"), text(r)
        assert len(fake.executes()) == 2, "each call must run exactly once"
    finally:
        fake.stop()


@check("a port that moves mid-session is rediscovered, and the call runs once")
def _t():
    old, new = FakeFusion(), FakeFusion()
    try:
        proxy, _, _ = make_proxy([old.url, new.url])
        call(proxy, "fusion_mcp_execute", execute(GOOD))
        old.stop()                                   # Fusion relaunched elsewhere
        r = call(proxy, "fusion_mcp_execute", execute(GOOD))
        assert not r.get("isError"), text(r)
        assert len(old.executes()) == 1 and len(new.executes()) == 1
        assert proxy.url == new.url
    finally:
        new.stop()


@check("a write Fusion took and never answered is NOT resent")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, log_dir = make_proxy(fake.url, BN_FUSION_TIMEOUT="0.5")
        proxy.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        fake.execute_delay = 1.5
        r = call(proxy, "fusion_mcp_execute", execute(GOOD))
        assert r["isError"] and "Do not resend a write" in text(r), text(r)
        time.sleep(1.6)
        assert len(fake.executes()) == 1, "a no-reply write was retried"
        assert log_records(log_dir)[-1]["outcome"] == "no-reply"
    finally:
        fake.stop()


@check("Fusion coming up mid-session triggers tools/list_changed")
def _t():
    fake = FakeFusion()
    try:
        proxy, sent, _ = make_proxy([DEAD_URL, fake.url])
        assert tool_names(proxy) == ["bn_fusion_status", "bn_snapshot"]
        assert sent == [], "the first probe is not a change"
        report = json.loads(text(call(proxy, "bn_fusion_status")))
        assert report["reachable"] is True and "fusion_mcp_execute" in report["fusion_tools"]
        assert {"jsonrpc": "2.0", "method": "notifications/tools/list_changed"} in sent
        assert "fusion_mcp_execute" in tool_names(proxy)
    finally:
        fake.stop()


# -- bn_snapshot ---------------------------------------------------------------

@check("bn_snapshot runs read-only and returns the inventory as structured data")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, log_dir = make_proxy(fake.url)
        r = call(proxy, "bn_snapshot", {"units": "mm", "detail": "summary"})
        assert not r.get("isError"), text(r)
        assert r["structuredContent"] == fake.snapshot
        sent = fake.executes()[-1]["object"]
        assert sent["readOnly"] is True
        assert "UNITS = 'mm'" in sent["script"] and "DETAIL = 'summary'" in sent["script"]
        logged = log_records(log_dir)[-1]
        assert logged["arguments"] == {"bn_snapshot": {"units": "mm", "detail": "summary"}}
    finally:
        fake.stop()


@check("bn_snapshot rejects bad options before anything reaches Fusion")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, _ = make_proxy(fake.url)
        r = call(proxy, "bn_snapshot", {"units": "furlongs"})
        assert r["isError"] and "units must be" in text(r)
        assert fake.executes() == []
    finally:
        fake.stop()


@check("bn_snapshot says so when the script printed no snapshot line")
def _t():
    fake = FakeFusion()
    try:
        proxy, _, _ = make_proxy(fake.url)
        fake._result = lambda name, args: {"content": [{"type": "text", "text": json.dumps(
            {"message": "Traceback: AttributeError", "success": False})}]}
        r = call(proxy, "bn_snapshot")
        assert r["isError"] and "no BN_SNAPSHOT line" in text(r)
        assert "AttributeError" in text(r), "Fusion's own output is shown"
    finally:
        fake.stop()


@check("the snapshot script is valid Python for every option")
def _t():
    fusion_snapshot.demo()


# -- the real stdio server, the way Claude launches it ----------------------------

@check("over stdio: initialize, tools/list and a call, via the real entry point")
def _t():
    fake = FakeFusion()
    log_dir = tempfile.mkdtemp(prefix="bn-proxy-log-")
    try:
        env = dict(os.environ, BN_FUSION_MCP_URL=fake.url, BN_FUSION_LOG_DIR=log_dir)
        lines = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "test", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "fusion_mcp_execute", "arguments": execute(GOOD)}},
        ]
        proc = subprocess.run(
            [sys.executable, str(HERE / "fusion_mcp_proxy.py")],
            input="".join(json.dumps(m) + "\n" for m in lines),
            capture_output=True, text=True, timeout=60, env=env)
        replies = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
        by_id = {r.get("id"): r for r in replies}
        assert set(by_id) == {1, 2, 3}, (replies, proc.stderr)
        assert by_id[1]["result"]["serverInfo"]["name"] == P.NAME
        assert "fusion_mcp_execute" in [t["name"] for t in by_id[2]["result"]["tools"]]
        assert "ran" in text(by_id[3]["result"])
        assert proc.returncode == 0, proc.stderr
    finally:
        fake.stop()
        shutil.rmtree(log_dir, ignore_errors=True)


@check("the bridge stays Python 3.8 syntax: a Mac runs it with whatever python3 it has")
def _t():
    import ast
    for name in ("fusion_mcp_proxy.py", "fusion_mcp.py", "fusion_snapshot.py",
                 "fusion_port.py"):
        ast.parse((HERE / name).read_text(), feature_version=(3, 8))


@check(".mcp.json launches this proxy, at a path that exists")
def _t():
    config = json.loads((REPO / ".mcp.json").read_text())
    server = config["mcpServers"]["fusion-desktop"]
    assert server["command"] == "python3"
    script = server["args"][0].replace("${CLAUDE_PROJECT_DIR:-.}", str(REPO))
    assert pathlib.Path(script).resolve() == (HERE / "fusion_mcp_proxy.py").resolve(), script


@check(".mcp.json pins build123d-mcp exactly, and the cloud hook warms that pin")
def _t():
    import re
    server = json.loads((REPO / ".mcp.json").read_text())["mcpServers"]["build123d"]
    pin = server["args"][-1]
    # An exact pin, never @latest: an upstream release must not change what
    # Claude's CAD tools do between one session and the next.
    assert re.fullmatch(r"build123d-mcp==\d+\.\d+\.\d+", pin), pin
    hook = (REPO / ".claude" / "hooks" / "session-start.sh").read_text()
    line = next(l for l in hook.splitlines() if l.startswith("B123D_PIN="))
    snippet = re.search(r"python3 -c '([^']+)'", line).group(1)
    got = subprocess.run([sys.executable, "-c", snippet, str(REPO / ".mcp.json")],
                         capture_output=True, text=True, timeout=30)
    assert got.stdout.strip() == pin, (got.stdout, got.stderr)


def main():
    print("fusion MCP proxy tests")
    for n in PASSED:
        print("  ok   %s" % n)
    for n, why in FAILED:
        print("  FAIL %s\n         %s" % (n, why))
    print("\n%d passed, %d failed" % (len(PASSED), len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
