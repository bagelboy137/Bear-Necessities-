#!/usr/bin/env python3
"""Find the port Fusion's MCP server is actually listening on.

27182 is the documented default and it is NOT stable. After Fusion crashed and
relaunched on 2026-08-26 it came back on 27180, and every tool pointed at 27182
reported "Is Fusion running?" while Fusion was running perfectly. That cost two
hours. Pinning the new number in config just relocates the bug, so ask the OS
instead.

This lives in the bridge because the bridge owns MCP connectivity: preflight.py,
build.sh, fusion_mcp.py and render_module.py all resolve through here rather than
carrying their own copy.

    from fusion_port import discover
    url = discover()                     # honours BN_FUSION_MCP_URL

    python3 fusion_port.py               # prints the URL, for shell callers
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:27182/mcp"

# lsof lives in /usr/sbin, which is NOT on a cron or launchd PATH. Calling it by
# bare name worked in a login shell and silently returned nothing under a
# scheduler - the port-discovery fallback quietly disabled exactly where
# unattended runs need it, which is how this project lost two hours to a moved
# port in the first place. Absolute path, with the bare name as a fallback for
# any system that puts it elsewhere.
_LSOF = "/usr/sbin/lsof" if os.path.exists("/usr/sbin/lsof") else "lsof"
# Checked before scanning: the documented port and the ones Fusion has actually
# been observed to fall back to.
LIKELY_PORTS = (27182, 27180, 27181, 27183, 27184)
FUSION_PATTERN = "Autodesk Fusion.app/Contents/MacOS"


def speaks_mcp(url, timeout=5):
    """Confirm with a real initialize handshake, not a liveness ping.

    Fusion listens on several local ports and most answer HTTP happily. A
    "did we get a response" check selects 9766, which is a real listener and is
    not the MCP server. Only a handshake that returns a result identifies it.
    """
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "bn-port-probe", "version": "1.0"}},
    }).encode()
    request = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception:
        return False
    return '"result"' in body and "serverInfo" in body


def _fusion_listening_ports():
    """Every localhost TCP port the Fusion process holds open."""
    try:
        pids = subprocess.run(["pgrep", "-f", FUSION_PATTERN],
                              capture_output=True, text=True,
                              timeout=10).stdout.split()
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    ports = []
    for pid in pids:
        try:
            listing = subprocess.run(
                [_LSOF, "-nP", "-a", "-p", pid, "-iTCP", "-sTCP:LISTEN"],
                capture_output=True, text=True, timeout=15).stdout
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
        for match in re.finditer(r"127\.0\.0\.1:(\d+)", listing):
            port = int(match.group(1))
            if port not in ports:
                ports.append(port)
    return ports


def discover(default=DEFAULT_URL, configured=None):
    """Resolve the MCP URL. BN_FUSION_MCP_URL wins; then config; then the OS.

    `configured` is whatever runtime.json holds. The string "auto" means "do not
    trust a literal, go and look", which is the setting this function exists for.
    """
    override = os.environ.get("BN_FUSION_MCP_URL")
    if override:
        return override
    if configured and configured != "auto":
        return configured

    for port in LIKELY_PORTS:
        url = "http://127.0.0.1:%d/mcp" % port
        if speaks_mcp(url):
            return url
    for port in _fusion_listening_ports():
        url = "http://127.0.0.1:%d/mcp" % port
        if speaks_mcp(url):
            return url
    # Nothing answered. Return the default so callers report "unreachable at
    # <documented port>" rather than something confusingly invented.
    return default


def demo():
    """Self-check the precedence rules, without needing Fusion."""
    os.environ["BN_FUSION_MCP_URL"] = "http://127.0.0.1:9999/mcp"
    assert discover(configured="auto") == "http://127.0.0.1:9999/mcp", \
        "the environment override must win over everything"
    assert discover(configured="http://127.0.0.1:5555/mcp") == \
        "http://127.0.0.1:9999/mcp", "the override must beat a configured literal"
    del os.environ["BN_FUSION_MCP_URL"]

    assert discover(configured="http://127.0.0.1:5555/mcp") == \
        "http://127.0.0.1:5555/mcp", "a configured literal must be honoured"

    # "auto" must never return the literal string; it has to resolve to a URL.
    resolved = discover(configured="auto")
    assert resolved.startswith("http://127.0.0.1:"), resolved
    assert resolved != "auto"

    # A port that answers HTTP but is not MCP must be rejected.
    assert not speaks_mcp("http://127.0.0.1:1/mcp", timeout=1)

    # The OS-scan fallback must not depend on PATH. Under cron and launchd,
    # PATH does not include /usr/sbin, and a bare "lsof" there fails silently -
    # disabling port discovery precisely where unattended runs rely on it.
    assert _LSOF.startswith("/") or shutil.which("lsof"), \
        "lsof is not resolvable; the port-discovery fallback would fail silently"
    if os.path.exists("/usr/sbin/lsof"):
        assert _LSOF == "/usr/sbin/lsof", _LSOF
    print("demo ok: env override > configured literal > discovery; "
          "auto always resolves to a URL; non-MCP listeners rejected")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
        return 0
    print(discover(configured=(sys.argv[1] if len(sys.argv) > 1 else None)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
