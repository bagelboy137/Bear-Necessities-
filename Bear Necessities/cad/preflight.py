#!/usr/bin/env python3
"""Report whether this machine can build the Bear Necessities CAD family.

Runs anywhere with stdlib Python 3.9+. It never mutates the study; it only
answers "what would fail if I started a build right now, and how do I fix it?"

    python3 preflight.py              # full report
    python3 preflight.py --for cad    # only the CadQuery/offline path
    python3 preflight.py --json       # machine-readable

Exit codes: 0 ready, 1 blocked, 2 configuration error.
"""

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
RUNTIME = HERE / "runtime.json"

# Which checks each build path needs. "cad" is the offline CadQuery path that
# works with nothing but Python; "revision" adds the local model; "native"
# additionally needs Fusion running with its MCP server.
SCOPES = {
    "cad": ("layout", "python", "cadquery"),
    "parts": ("layout", "python", "cadquery", "bncad", "sandbox", "lmstudio"),
    "revision": ("layout", "python", "lmstudio", "reviewer_model"),
    "native": ("layout", "python", "lmstudio", "reviewer_model", "vision_model", "fusion"),
    "visuals": ("layout", "python", "cadquery", "lmstudio", "visual_text_model",
                "visual_vision_model", "fusion"),
    "all": ("layout", "python", "cadquery", "bncad", "sandbox", "lmstudio",
            "reviewer_model", "vision_model", "visual_text_model",
            "visual_vision_model", "fusion"),
}

OK, WARN, FAIL = "OK", "WARN", "FAIL"


class Result:
    def __init__(self, name, status, detail, fix=""):
        self.name = name
        self.status = status
        self.detail = detail
        self.fix = fix

    def as_dict(self):
        return {"check": self.name, "status": self.status,
                "detail": self.detail, "fix": self.fix}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_runtime():
    if not RUNTIME.is_file():
        sys.exit("missing %s" % RUNTIME)
    return json.loads(RUNTIME.read_text())


def discover_root(config):
    override = os.environ.get("BN_CLAUDE_ROOT") or config["paths"]["claude_root"]
    if override and override != "auto":
        return pathlib.Path(override).expanduser().resolve()
    fusion = config["paths"]["fusion_project"]
    mini = config["paths"]["mac_mini_project"]
    for parent in HERE.parents:
        if (parent / fusion).is_dir() and (parent / mini).is_dir():
            return parent
    sys.exit("Could not discover the shared Claude root above %s. "
             "Set BN_CLAUDE_ROOT." % HERE)


def setting(config, section, key, env_key):
    return os.environ.get(env_key) or config[section][key]


def http_json(url, timeout=10):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as response:
        return json.load(response)


def check_layout(config, root):
    missing = []
    for key in ("fusion_project", "mac_mini_project", "cad_agent", "study"):
        if not (root / config["paths"][key]).is_dir():
            missing.append(config["paths"][key])
    if missing:
        return Result("project layout", FAIL,
                      "missing under %s: %s" % (root, ", ".join(missing)),
                      "Check out the whole Claude folder, or set BN_CLAUDE_ROOT "
                      "to the copy that has both sibling projects.")
    return Result("project layout", OK, "root %s" % root)


def check_python():
    version = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info < (3, 9):
        return Result("python", FAIL, "running %s" % version,
                      "Install Python 3.9 or newer.")
    return Result("python", OK, "%s at %s" % (version, sys.executable))


def check_cadquery(config, root):
    venv = root / config["paths"]["cadquery_venv"]
    interpreter = venv / "bin" / "python"
    if not interpreter.is_file():
        # uv is what actually built this venv, and it also fetches the
        # interpreter. On a fresh machine there is no system python3.12 to run,
        # so leading with the plain-venv command sends you to a "command not
        # found" instead of a working environment.
        return Result("cadquery venv", FAIL, "no interpreter at %s" % interpreter,
                      "uv venv --python 3.12 '%s' && uv pip install --python "
                      "'%s' cadquery   (or, if you already have a 3.12: "
                      "python3.12 -m venv '%s' && '%s' -m pip install cadquery)"
                      % (venv, interpreter, venv, interpreter))
    probe = subprocess.run(
        [str(interpreter), "-c",
         "import cadquery, sys; print(cadquery.__version__ + ' on ' + sys.version.split()[0])"],
        capture_output=True, text=True)
    if probe.returncode != 0:
        return Result("cadquery venv", FAIL,
                      "import failed: %s" % probe.stderr.strip().splitlines()[-1:],
                      "'%s' -m pip install --upgrade cadquery" % interpreter)
    return Result("cadquery venv", OK, "cadquery %s" % probe.stdout.strip())


def check_bncad(config, root):
    """The headless part-building package and its spec library."""
    venv = root / config["paths"]["cadquery_venv"]
    interpreter = venv / "bin" / "python"
    agent = root / config["paths"]["fusion_project"]
    if not (agent / "bncad" / "__init__.py").is_file():
        return Result("bncad", FAIL, "package missing at %s" % (agent / "bncad"),
                      "The bncad package belongs alongside bridge/ in that project.")
    if not interpreter.is_file():
        return Result("bncad", FAIL, "no CadQuery interpreter to run it with",
                      "See the cadquery venv fix above.")
    probe = subprocess.run(
        [str(interpreter), "-c",
         "import sys, pathlib; sys.path.insert(0, %r); import bncad; "
         "from bncad.spec import PartSpec; "
         "d = pathlib.Path(%r) / 'specs' / 'parts'; "
         "n = [PartSpec.load(f) for f in sorted(d.glob('*.json'))]; "
         "print('%%s, %%d spec(s)' %% (bncad.__version__, len(n)))"
         % (str(agent), str(agent))],
        capture_output=True, text=True)
    if probe.returncode != 0:
        tail = (probe.stderr or probe.stdout).strip().splitlines()[-1:]
        return Result("bncad", FAIL, "import or spec load failed: %s" % tail,
                      "Run: '%s' -m bncad selftest" % interpreter)
    detail = probe.stdout.strip()
    if detail.endswith("0 spec(s)"):
        return Result("bncad", WARN, detail,
                      "No part specs in %s - nothing for './build.sh parts' to build."
                      % (agent / "specs" / "parts"))
    return Result("bncad", OK, detail)


def check_sandbox():
    """Generated model code must run confined. No sandbox, no headless builds."""
    binary = "/usr/bin/sandbox-exec"
    if not os.path.exists(binary):
        return Result("sandbox", FAIL, "sandbox-exec not found",
                      "Without it, model-written Python would run unconfined, and "
                      "bncad refuses to treat that as acceptable.")
    return Result("sandbox", OK, binary)


def lm_models(url):
    return [item["id"] for item in http_json(url.rstrip("/") + "/models").get("data", [])]


def check_lmstudio(url):
    try:
        models = lm_models(url)
    except (urllib.error.URLError, OSError) as exc:
        return Result("LM Studio", FAIL, "unreachable at %s (%s)" % (url, exc),
                      "Start the LM Studio server, or on the mini run "
                      "'Mac Mini Setup/tools/local-ai/ensure-llmstudio.sh'. "
                      "Override the address with BN_LM_STUDIO_URL."), []
    if not models:
        return Result("LM Studio", FAIL, "server up at %s but no model loaded" % url,
                      "Load a model in LM Studio (lms load <model>)."), []
    return Result("LM Studio", OK, "%d model(s) at %s" % (len(models), url)), models


def check_model(role, wanted, models, env_key):
    if not models:
        return Result("%s model" % role, FAIL, "cannot check; LM Studio is not answering",
                      "Fix LM Studio first.")
    if wanted in models:
        return Result("%s model" % role, OK, wanted)
    return Result("%s model" % role, FAIL,
                  "%r not loaded; available: %s" % (wanted, ", ".join(models)),
                  "Load it in LM Studio, or point this role at one of the "
                  "available ids with %s=<id>." % env_key)


def resolve_fusion_url(root, configured, config):
    """Ask the bridge where Fusion actually is, rather than trusting a literal.

    `config` is passed in rather than read from a global: the except below is
    broad enough to swallow a NameError, so a scoping mistake here would look
    exactly like "Fusion is on the default port" and silently undo the port
    discovery this project needed two hours to learn it wanted.
    """
    bridge = pathlib.Path(root) / config["paths"]["fusion_project"] / "bridge"
    try:
        sys.path.insert(0, str(bridge))
        from fusion_port import discover
        return discover(configured=configured)
    except Exception:
        return configured if configured and configured != "auto" else \
            "http://127.0.0.1:27182/mcp"


def check_fusion(url):
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "bn-preflight", "version": "1"}},
    }).encode()
    request = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except (urllib.error.URLError, OSError) as exc:
        return Result("Fusion MCP", FAIL, "unreachable at %s (%s)" % (url, exc),
                      "Launch Autodesk Fusion and sign in; its MCP server listens "
                      "on a local port only while the app is running, and that "
                      "port is not fixed - this was discovered, not assumed. "
                      "Override with BN_FUSION_MCP_URL. The 'cad' and 'revision' "
                      "scopes do not need this.")
    return Result("Fusion MCP", OK, "responding at %s" % url)


def gate_state(config, root):
    """Report the study's current gate evidence without re-running anything."""
    study = root / config["paths"]["study"]
    lines = []
    ledger = study / "iterations" / "runs" / "iteration-ledger.json"
    if ledger.is_file():
        data = json.loads(ledger.read_text())
        lines.append("revision ledger: %s (%s of %s module reviews)" % (
            data.get("result"), data.get("module_review_count"),
            data.get("expected_module_review_count")))
    else:
        lines.append("revision ledger: absent")
    report = study / "fusion-native" / "exports" / "native-validation-report.json"
    validator = study / "fusion_native" / "validate_native_family.py"
    if report.is_file():
        data = json.loads(report.read_text())
        note = ""
        recorded = data.get("validator_sha256")
        if not recorded:
            note = "  [STALE: produced before the gate recorded its own identity; re-run it]"
        elif validator.is_file() and recorded != sha256(validator):
            note = "  [STALE: the validator has changed since this report; re-run it]"
        lines.append("native family gate: %s (%d failure(s))%s" % (
            data.get("result"), len(data.get("failures", [])), note))
    else:
        lines.append("native family gate: absent")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--for", dest="scope", choices=sorted(SCOPES), default="all")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_runtime()
    root = discover_root(config)
    wanted = SCOPES[args.scope]

    lm_url = setting(config, "services", "lm_studio_url", "BN_LM_STUDIO_URL")
    fusion_url = resolve_fusion_url(
        root, setting(config, "services", "fusion_mcp_url", "BN_FUSION_MCP_URL"),
        config)
    reviewer = setting(config, "models", "reviewer", "BN_REVIEWER_MODEL")
    vision = setting(config, "models", "vision", "BN_VISION_MODEL")
    visual_text = setting(config, "models", "visual_text", "BN_VISUAL_TEXT_MODEL")
    visual_vision = setting(config, "models", "visual_vision", "BN_VISUAL_VISION_MODEL")

    results = []
    models = []
    if "layout" in wanted:
        results.append(check_layout(config, root))
    if "python" in wanted:
        results.append(check_python())
    if "cadquery" in wanted:
        results.append(check_cadquery(config, root))
    if "bncad" in wanted:
        results.append(check_bncad(config, root))
    if "sandbox" in wanted:
        results.append(check_sandbox())
    if "lmstudio" in wanted:
        result, models = check_lmstudio(lm_url)
        results.append(result)
    if "reviewer_model" in wanted:
        results.append(check_model("reviewer", reviewer, models, "BN_REVIEWER_MODEL"))
    if "vision_model" in wanted:
        results.append(check_model("vision", vision, models, "BN_VISION_MODEL"))
    if "visual_text_model" in wanted:
        results.append(check_model("visual text", visual_text, models,
                                   "BN_VISUAL_TEXT_MODEL"))
    if "visual_vision_model" in wanted:
        results.append(check_model("visual vision", visual_vision, models,
                                   "BN_VISUAL_VISION_MODEL"))
    if "fusion" in wanted:
        results.append(check_fusion(fusion_url))

    blocked = [item for item in results if item.status == FAIL]
    state = gate_state(config, root)

    if args.json:
        print(json.dumps({
            "scope": args.scope,
            "claude_root": str(root),
            "ready": not blocked,
            "checks": [item.as_dict() for item in results],
            "gate_state": state,
        }, indent=2))
        return 1 if blocked else 0

    width = max(len(item.name) for item in results)
    print("Bear Necessities CAD preflight — scope '%s'" % args.scope)
    print("root: %s\n" % root)
    for item in results:
        print("  [%-4s] %-*s  %s" % (item.status, width, item.name, item.detail))
    print("\nCurrent gate evidence (not re-run by preflight):")
    for line in state:
        print("  - %s" % line)
    if blocked:
        print("\nBLOCKED — %d check(s) failed:" % len(blocked))
        for item in blocked:
            print("\n  %s: %s\n    fix: %s" % (item.name, item.detail, item.fix))
        return 1
    print("\nREADY for scope '%s'." % args.scope)
    return 0


if __name__ == "__main__":
    sys.exit(main())
