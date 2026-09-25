#!/usr/bin/env bash
# Bear Necessities CAD build front door.
#
# One command that works the same on Conor's laptop and on the Mac mini. All
# machine-specific values come from runtime.json or BN_* environment variables;
# nothing here assumes a home directory.
#
#   ./build.sh test         run the framework test suites
#   ./build.sh validate     re-run every deterministic gate (no model, no Fusion)
#   ./build.sh revision     run the local-model review cycles (needs LM Studio)
#   ./build.sh native       rebuild the native Fusion family (needs Fusion + LM Studio)
#   ./build.sh visuals      render and review marketing images (Fusion + LM Studio)
#   ./build.sh parts        build the bncad part library from specs (needs a local model)
#   ./build.sh all          test, revision, native, visuals, then validate
#
# Add --skip-preflight only when you have already checked readiness.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
STAGE="${1:-validate}"
shift || true

SKIP_PREFLIGHT=0
for arg in "$@"; do
  [ "$arg" = "--skip-preflight" ] && SKIP_PREFLIGHT=1
done

# Resolve runtime settings once, honouring BN_* overrides.
eval "$(python3 - "$HERE" <<'PY'
import json, os, pathlib, shlex, sys
here = pathlib.Path(sys.argv[1])
config = json.loads((here / "runtime.json").read_text())

root = os.environ.get("BN_CLAUDE_ROOT") or config["paths"]["claude_root"]
if not root or root == "auto":
    for parent in here.resolve().parents:
        if ((parent / config["paths"]["fusion_project"]).is_dir()
                and (parent / config["paths"]["mac_mini_project"]).is_dir()):
            root = str(parent)
            break
    else:
        sys.exit("could not discover the Claude root; set BN_CLAUDE_ROOT")

def _fusion_url(root, configured):
    # The Fusion MCP port is not stable: it moved from 27182 to 27180 after a
    # crash-relaunch. Ask the bridge to find it rather than trusting a literal.
    sys.path.insert(0, str(pathlib.Path(root) / config["paths"]["fusion_project"] / "bridge"))
    try:
        from fusion_port import discover
        return discover(configured=configured)
    except Exception:
        return os.environ.get("BN_FUSION_MCP_URL") or (
            configured if configured != "auto" else "http://127.0.0.1:27182/mcp")


values = {
    "BN_ROOT": root,
    "BN_STUDY": str(pathlib.Path(root) / config["paths"]["study"]),
    "BN_LM_URL": os.environ.get("BN_LM_STUDIO_URL") or config["services"]["lm_studio_url"],
    "BN_FUSION_URL": _fusion_url(root, config["services"]["fusion_mcp_url"]),
    "BN_REVIEWER": os.environ.get("BN_REVIEWER_MODEL") or config["models"]["reviewer"],
    "BN_VISION": os.environ.get("BN_VISION_MODEL") or config["models"]["vision"],
    "BN_VISUAL_TEXT": os.environ.get("BN_VISUAL_TEXT_MODEL") or config["models"]["visual_text"],
    "BN_VISUAL_VISION": os.environ.get("BN_VISUAL_VISION_MODEL") or config["models"]["visual_vision"],
    "BN_REVIEWS": str(os.environ.get("BN_EXPECTED_REVIEWS")
                      or config["gates"]["expected_module_reviews"]),
    "BN_ATTEMPTS": str(config["gates"]["revision_attempts"]),
    "BN_VISUAL_CYCLES": str(config["gates"]["visual_cycles"]),
    "BN_VISUAL_REVIEWS": str(config["gates"]["expected_visual_reviews"]),
    "BN_VENV_PY": str(pathlib.Path(root) / config["paths"]["cadquery_venv"] / "bin" / "python"),
    "BN_AGENT": str(pathlib.Path(root) / config["paths"]["cad_agent"]),
    # Resolved from config rather than spelled out at each use. The key was
    # configurable but every call site hard-coded "Fusion CAD Agent", so
    # changing it moved nothing and broke discovery silently.
    "BN_FUSION_DIR": str(pathlib.Path(root) / config["paths"]["fusion_project"]),
}
for key, value in values.items():
    print("%s=%s" % (key, shlex.quote(str(value))))
PY
)"

ITER="$BN_STUDY/iterations"
NATIVE="$BN_STUDY/fusion_native"
VISUAL="$BN_STUDY/visual"

preflight() {
  [ "$SKIP_PREFLIGHT" = "1" ] && return 0
  python3 "$HERE/preflight.py" --for "$1"
}

run_revision() {
  echo "==> local-model revision cycles (${BN_REVIEWER})"
  # Completed cycles are reused, so an interrupted run resumes instead of
  # restarting the whole 30-cycle sweep.
  python3 "$ITER/run_revision_cycles.py" \
    --endpoint "$BN_LM_URL" --model "$BN_REVIEWER" \
    --stage all --attempts "$BN_ATTEMPTS"
  python3 "$ITER/validate_revision_ledger.py" "$ITER/runs/iteration-ledger.json"
  python3 "$ITER/summarize_iteration_learnings.py" --ledger "$ITER/runs/iteration-ledger.json"
}

run_native() {
  echo "==> native Fusion family rebuild"
  python3 "$NATIVE/run_native_pipeline.py" \
    --fusion-url "$BN_FUSION_URL" --lm-url "$BN_LM_URL" \
    --vision-model "$BN_VISION" \
    --revision-ledger "$ITER/runs/iteration-ledger.json" \
    --ots-catalog "$ITER/ots-components.json" \
    --expected-reviews "$BN_REVIEWS"
}

run_visuals() {
  echo "==> marketing render + local-model visual cycles"
  "$BN_VENV_PY" "$VISUAL/run_visual_cycles.py" \
    --cycles "$BN_VISUAL_CYCLES" \
    --endpoint "$BN_LM_URL/chat/completions" \
    --text-model "$BN_VISUAL_TEXT" \
    --vision-model "$BN_VISUAL_VISION"
  "$BN_VENV_PY" "$VISUAL/validate_visual_ledger.py" \
    --min-cycles "$BN_VISUAL_CYCLES" --min-reviews "$BN_VISUAL_REVIEWS"
  "$BN_VENV_PY" "$VISUAL/visual_quality.py" --all
}

run_validate() {
  echo "==> deterministic gates"
  python3 "$BN_STUDY/validate_family.py"
  python3 "$BN_STUDY/validate_jobs.py"
  python3 "$BN_STUDY/mesh_integrity.py" \
    --jobs "$BN_STUDY/jobs" --exports "$BN_STUDY/exports" \
    --output "$BN_STUDY/mesh-integrity-report.json"
  # The native gate is expected to fail until the revision ledger is complete.
  # Report it rather than hiding it.
  python3 "$NATIVE/validate_native_family.py" --expected-reviews "$BN_REVIEWS" || true
}

run_tests() {
  # The suites need ezdxf and cadquery, which live in the project venv, not in
  # the system interpreter. Running them with plain python3 silently skips the
  # drawing tests with an import error.
  if [ ! -x "$BN_VENV_PY" ]; then
    echo "missing CadQuery venv interpreter at $BN_VENV_PY" >&2
    echo "run: python3 preflight.py --for cad" >&2
    exit 1
  fi
  echo "==> framework tests ($BN_VENV_PY)"
  (cd "$BN_AGENT" && "$BN_VENV_PY" -m unittest discover -s tests)
  echo "==> bncad self-test (no model, no Fusion, no network)"
  (cd "$BN_FUSION_DIR" && "$BN_VENV_PY" -m bncad selftest)
}

run_parts() {
  # Headless: CadQuery builds the solids, so this needs a local model but not
  # Fusion. That is what makes it the overnight-safe way to produce geometry.
  echo "==> bncad part library (${BN_REVIEWER})"
  (cd "$BN_FUSION_DIR" && \
    BN_MODEL="$BN_REVIEWER" "$BN_VENV_PY" -m bncad bench --attempts 6)
}

case "$STAGE" in
  test)     preflight cad;      run_tests ;;
  validate) preflight cad;      run_validate ;;
  revision) preflight revision; run_revision ;;
  native)   preflight native;   run_native ;;
  visuals)  preflight visuals;  run_visuals ;;
  parts)    preflight parts;    run_parts ;;
  all)      preflight all;      run_tests; run_revision; run_native; run_visuals; run_validate ;;
  *) echo "usage: $0 {test|validate|revision|native|visuals|parts|all} [--skip-preflight]" >&2; exit 2 ;;
esac
