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
import argparse, json, os, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

    def _post(self, payload, expect_reply=True):
        self._id += 1
        payload.setdefault("jsonrpc", "2.0")
        if expect_reply:
            payload["id"] = self._id
        h = dict(HDRS)
        if self.sid:
            h["MCP-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(),
                                     headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                if self.sid is None:
                    self.sid = r.headers.get("MCP-Session-Id")
                body = r.read().decode()
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot reach Fusion MCP at {self.url}: {e}\n"
                "Is Fusion running, and is 'Fusion MCP Server' ticked in "
                "Preferences > General > API?") from None
        if not body.strip():
            return None
        # streamable-http may frame replies as SSE
        if body.lstrip().startswith("event:") or body.lstrip().startswith("data:"):
            for line in body.splitlines():
                if line.startswith("data:"):
                    body = line[5:].strip()
                    break
        return json.loads(body)

    def connect(self):
        r = self._post({"method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "bear-necessities-cad", "version": "1.0"}}})
        # REQUIRED: without this the server rejects everything with
        # "Session not initialized" even though initialize returned 200.
        self._post({"method": "notifications/initialized", "params": {}},
                   expect_reply=False)
        return r.get("result", {})

    def tools(self):
        return self._post({"method": "tools/list", "params": {}}).get("result", {}).get("tools", [])

    def call(self, name, args):
        r = self._post({"method": "tools/call",
                        "params": {"name": name, "arguments": args}})
        if "error" in r:
            raise RuntimeError(json.dumps(r["error"]))
        res = r.get("result", {})
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
