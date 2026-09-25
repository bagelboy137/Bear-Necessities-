#!/usr/bin/env python3
"""Small stdlib client for Autodesk Fusion's local streamable-HTTP MCP API."""

import json
import urllib.error
import urllib.request


DEFAULT_URL = "http://127.0.0.1:27182/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class FusionAPIError(RuntimeError):
    pass


class FusionMCPClient:
    def __init__(self, url=DEFAULT_URL, timeout=1800):
        self.url = url
        self.timeout = timeout
        self.session_id = None
        self.request_id = 0

    @staticmethod
    def _decode(body, request_id=None):
        body = body.strip()
        if not body:
            return None
        if body.startswith("{"):
            return json.loads(body)
        events = []
        for line in body.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                if raw and raw != "[DONE]":
                    events.append(json.loads(raw))
        if request_id is not None:
            for event in events:
                if event.get("id") == request_id:
                    return event
        return events[-1] if events else None

    def _post(self, method, params=None, notification=False):
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "method": method,
                   "params": params or {}}
        if not notification:
            payload["id"] = self.request_id
        headers = dict(HEADERS)
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if not self.session_id:
                    self.session_id = response.headers.get("MCP-Session-Id")
                body = response.read().decode("utf-8", "replace")
        except urllib.error.URLError as exc:
            raise FusionAPIError(
                "Cannot reach Fusion MCP at %s: %s. Start Fusion and enable "
                "Preferences > General > API > Fusion MCP Server." %
                (self.url, exc)
            ) from None
        result = self._decode(body, None if notification else self.request_id)
        if result and result.get("error"):
            raise FusionAPIError(json.dumps(result["error"]))
        return result

    def connect(self):
        response = self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "bn-native-cad-pipeline", "version": "1.0"},
        })
        self._post("notifications/initialized", {}, notification=True)
        return (response or {}).get("result", {})

    def list_tools(self):
        response = self._post("tools/list")
        return (response or {}).get("result", {}).get("tools", [])

    def call_tool(self, name, arguments):
        response = self._post("tools/call", {"name": name, "arguments": arguments})
        result = (response or {}).get("result", {})
        text = "\n".join(
            item.get("text", "") for item in result.get("content", [])
            if item.get("type") == "text"
        )
        return text, bool(result.get("isError", False))

    def execute_script(self, source):
        return self.call_tool("fusion_mcp_execute", {
            "featureType": "script",
            "object": {"script": source},
        })

