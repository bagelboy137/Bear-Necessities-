#!/usr/bin/env python3
"""
fusion_mcp.py — minimal client for Fusion's built-in MCP server.

Fusion 2704+ ships an MCP server (Preferences > General > API > "Fusion MCP
Server"), default http://127.0.0.1:27182/mcp. It exposes Create/Read/Update/
Delete/Execute against the LIVE Fusion session.

This obsoletes the watcher-add-in design: Execute runs a Python script inside
Fusion and returns stdout AND exceptions, which is the closed feedback loop.

    python3 bridge/fusion_mcp.py --list
    python3 bridge/fusion_mcp.py --exec-file script.py
    python3 bridge/fusion_mcp.py --exec 'def run(_context: str):\n    print("hi")'
"""
import argparse, json, os, socket, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Typed failures, because what a caller may safely do next depends on which one
# it was. All three stay RuntimeErrors so existing `except Exception` callers
# behave exactly as before.
class FusionUnreachable(RuntimeError):
    """Nothing answered: Fusion is closed, the MCP server is off, or the port
    moved. The request never arrived, so retrying after rediscovery is safe."""


class FusionNoReply(RuntimeError):
    """Fusion accepted the request and then went quiet (timeout or dropped
    connection). It may still have run it - inspect before retrying a write."""


class FusionHTTPError(RuntimeError):
    """The server answered with an HTTP error, e.g. a session it has forgotten
    after a relaunch."""

    def __init__(self, code, body, url):
        self.code, self.body = code, body
        super().__init__("HTTP %s from %s: %s" % (code, url, body[:300]))


# The version this client has been verified against live Fusion with. Newer
# versions require an MCP-Protocol-Version header on every later request, which
# _post adds whenever the server negotiates something else.
PROTOCOL = "2024-11-05"

def _default_url():
    # The documented 27182 is not reliable; fusion_port asks the OS which port
    # Fusion is really on. Falls back to the documented value if that fails.
    try:
        from fusion_port import discover
        return discover(configured="auto")
    except Exception:
        return os.environ.get("BN_FUSION_MCP_URL", "http://127.0.0.1:27182/mcp")


URL = _default_url()
HDRS = {"Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"}


class FusionMCP:
    def __init__(self, url=URL, timeout=300):
        self.url, self.timeout, self.sid, self._id = url, timeout, None, 0
        self.protocol, self.server_info = None, {}

    def _post(self, payload, expect_reply=True):
        self._id += 1
        payload.setdefault("jsonrpc", "2.0")
        if expect_reply:
            payload["id"] = self._id
        h = dict(HDRS)
        if self.sid:
            h["MCP-Session-Id"] = self.sid
        if self.protocol and self.protocol != PROTOCOL:
            h["MCP-Protocol-Version"] = self.protocol
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(),
                                     headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                if self.sid is None:
                    self.sid = r.headers.get("MCP-Session-Id")
                body = r.read().decode()
        except urllib.error.HTTPError as e:
            # HTTPError is a URLError; caught first so a server that answered
            # is never reported as "is Fusion running?".
            detail = e.read(2048).decode("utf-8", "replace") if e.fp else ""
            raise FusionHTTPError(e.code, detail, self.url) from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise FusionNoReply(
                    f"Fusion MCP at {self.url} did not answer within "
                    f"{self.timeout}s.") from None
            raise FusionUnreachable(
                f"Cannot reach Fusion MCP at {self.url}: {e}\n"
                "Is Fusion running, and is 'Fusion MCP Server' ticked in "
                "Preferences > General > API?") from None
        except (socket.timeout, TimeoutError, ConnectionError) as e:
            # Raised while reading the reply, i.e. after Fusion had the request.
            raise FusionNoReply(
                f"Fusion MCP at {self.url} stopped answering mid-request "
                f"({type(e).__name__}).") from None
        if not body.strip():
            return None
        # streamable-http may frame replies as SSE, possibly several events;
        # the reply is the one carrying this request's id.
        if body.lstrip().startswith("event:") or body.lstrip().startswith("data:"):
            events = [line[5:].strip() for line in body.splitlines()
                      if line.startswith("data:") and line[5:].strip()]
            for event in events:
                try:
                    msg = json.loads(event)
                except ValueError:
                    continue
                if not expect_reply or (isinstance(msg, dict)
                                        and msg.get("id") == payload.get("id")):
                    return msg
            body = events[0] if events else "null"
        return json.loads(body)

    def connect(self):
        r = self._post({"method": "initialize", "params": {
            "protocolVersion": PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "bear-necessities-cad", "version": "1.0"}}})
        result = (r or {}).get("result", {})
        # Only after initialize: the version header must not go on it.
        self.protocol = result.get("protocolVersion") or PROTOCOL
        self.server_info = result.get("serverInfo", {})
        # REQUIRED: without this the server rejects everything with
        # "Session not initialized" even though initialize returned 200.
        self._post({"method": "notifications/initialized", "params": {}},
                   expect_reply=False)
        return result

    def tools(self):
        return self._post({"method": "tools/list", "params": {}}).get("result", {}).get("tools", [])

    def call_raw(self, name, args):
        """The tool result exactly as Fusion sent it: every content block,
        images included, plus structuredContent and isError."""
        r = self._post({"method": "tools/call",
                        "params": {"name": name, "arguments": args}})
        if not isinstance(r, dict):
            raise RuntimeError("Fusion returned no JSON-RPC reply to %s" % name)
        if "error" in r:
            raise RuntimeError(json.dumps(r["error"]))
        return r.get("result", {})

    def call(self, name, args):
        res = self.call_raw(name, args)
        out = "\n".join(c.get("text", "") for c in res.get("content", [])
                        if c.get("type") == "text")
        return out, res.get("isError", False)

    def run_script(self, src):
        """Execute Python inside Fusion. Returns (output, is_error)."""
        return self.call("fusion_mcp_execute",
                         {"featureType": "script", "object": {"script": src}})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--exec")
    ap.add_argument("--exec-file")
    ap.add_argument("--url", default=URL)
    a = ap.parse_args()

    m = FusionMCP(a.url)
    info = m.connect()
    print(f"connected: {info.get('serverInfo', {})}", file=sys.stderr)

    if a.list:
        for t in m.tools():
            desc = (t.get("description") or "").strip().splitlines()
            print(f"{t['name']}: {desc[0][:100] if desc else ''}")
        return 0

    src = None
    if a.exec_file:
        src = open(a.exec_file).read()
    elif a.exec:
        src = a.exec.replace("\\n", "\n")
    if src:
        out, err = m.run_script(src)
        print(out)
        return 1 if err else 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
