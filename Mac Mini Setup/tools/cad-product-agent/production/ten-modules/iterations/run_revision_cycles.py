#!/usr/bin/env python3
"""Run schema-gated Qwen review cycles and preserve an auditable learning ledger.

One LM Studio call reviews all ten modules for one criterion.  Ten calls per
stage therefore produce ten review cycles for every module.  The local model is
an advisory proposer: this runner validates identifiers and provenance, records
REVISE findings as design requirements, and never lets the model invent or
release CAD, supplier data, safety claims, or purchase approval.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request


HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_ENDPOINT = "http://127.0.0.1:1234/v1"
PRIMARY_MODEL = "qwen/qwen2.5-coder-14b"
LOW_MEMORY_MODEL = "qwen2.5-coder-7b-instruct"
DEFAULT_MODEL = PRIMARY_MODEL
APPROVED_MODELS = frozenset((PRIMARY_MODEL, LOW_MEMORY_MODEL))
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]
STAGES = ("design", "manufacturing", "combined")
DEFAULT_ATTEMPTS = 4
GLOBAL_EVIDENCE = {"CURRENT-CAD", "FRAME-CONSTRAINTS", "RELEASE-BOUNDARY"}
URL_RE = re.compile(r"https?://|www\.", re.I)
FIELD_LIMITS = {
    "proposal": (8, 320),
    "rationale": (8, 320),
    "acceptance_check": (8, 240),
    "risk": (4, 200),
}
UNSOURCED_CLAIM_RE = re.compile(
    r"\b(certified|certification|guaranteed|production[- ]ready|safe to fabricate|"
    r"approved for vehicle|meets (?:all )?(?:codes|standards))\b", re.I
)


class CycleError(RuntimeError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value):
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def extract_json(text):
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S | re.I)
    candidate = (fenced.group(1) if fenced else text).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            return json.loads(candidate[start:end + 1])
        raise


def lm_models(base_url):
    request = urllib.request.Request(base_url.rstrip("/") + "/models")
    with urllib.request.urlopen(request, timeout=20) as response:
        return [item["id"] for item in json.load(response).get("data", [])]


def memory_free_percent():
    """Return macOS's pressure-aware free percentage, or None elsewhere."""
    try:
        result = subprocess.run(
            ["memory_pressure", "-Q"], capture_output=True, text=True,
            timeout=10, check=False
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", result.stdout)
    return int(match.group(1)) if match else None


def wait_for_resources(max_load, min_free_percent, poll_seconds, timeout_seconds):
    """Do not begin another Metal inference while the laptop is already busy."""
    started = time.monotonic()
    announced = False
    while True:
        load = os.getloadavg()[0]
        free = memory_free_percent()
        load_ok = max_load <= 0 or load <= max_load
        memory_ok = free is None or min_free_percent <= 0 or free >= min_free_percent
        if load_ok and memory_ok:
            if announced:
                print("RESOURCE_GUARD_PASS load=%.2f free=%s%%" %
                      (load, "unknown" if free is None else free), flush=True)
            return
        if not announced:
            print("RESOURCE_GUARD_WAIT load=%.2f/%s free=%s/%s%%" % (
                load, max_load, "unknown" if free is None else free,
                min_free_percent
            ), flush=True)
            announced = True
        if time.monotonic() - started >= timeout_seconds:
            raise CycleError(
                "resource guard timed out: load %.2f (max %.2f), free %s%% (min %d%%)" %
                (load, max_load, "unknown" if free is None else free,
                 min_free_percent)
            )
        time.sleep(poll_seconds)


def call_model(base_url, model, messages, max_tokens=2000, resource_guard=None):
    if resource_guard:
        wait_for_resources(**resource_guard)
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LM_API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["LM_API_TOKEN"]
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=1800) as response:
        body = json.load(response)
    message = body["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning_content") or ""
    return content, body.get("usage", {})


def source_maps(context, comparable, catalog):
    comp_by_module = {module_id: [] for module_id in MODULE_IDS}
    for item in comparable["sources"]:
        for module_id in item["modules"]:
            comp_by_module[module_id].append(item)
    catalog_by_id = {item["id"]: item for item in catalog["components"]}
    module_by_id = {item["module_id"]: item for item in context["modules"]}
    return module_by_id, comp_by_module, catalog_by_id


def evidence_for(stage, module, comp_by_module, catalog_by_id):
    ids = set(GLOBAL_EVIDENCE)
    if stage in ("design", "combined"):
        ids.update(item["id"] for item in comp_by_module[module["module_id"]])
    if stage in ("manufacturing", "combined"):
        ids.update(item for item in module["primary_catalog_ids"] if item in catalog_by_id)
        ids.update({"TNUTZ-EX1010-18", "TNUTZ-EX1010-22", "8020-4132",
                    "8020-3393", "TAP-HYPACT-PANEL", "TNUTZ-GAS010A",
                    "TNUTZ-BUM010TS", "TNUTZ-HAN015AL"})
    return ids


def prompt_for(stage, cycle, criterion, context, comparable, catalog, prior):
    module_by_id, comp_by_module, catalog_by_id = source_maps(context, comparable, catalog)
    module_lines = []
    evidence_lines = []
    for module_id in MODULE_IDS:
        module = module_by_id[module_id]
        module_lines.append(
            "%s %s | visible: %s | deployment: %s | manufacturing: %s" % (
                module_id, module["name"], module["signature"],
                module["deployment"], module["manufacturing_focus"]
            )
        )
        evidence_lines.append("%s allowed evidence: %s" % (
            module_id, ", ".join(sorted(evidence_for(
                stage, module, comp_by_module, catalog_by_id
            )))
        ))
    prior_lines = []
    for module_id in MODULE_IDS:
        recent = [item for item in prior if item["module_id"] == module_id][-3:]
        if recent:
            prior_lines.append("%s recent: %s" % (
                module_id, " | ".join(item["proposal"] for item in recent)
            ))
    return """You are the local offline revision proposer for a ten-module overland CAD family.
This is criterion {cycle}/10 in the {stage} stage.
Criterion: {criterion_name}
Question: {question}

Review every module independently. Choose REVISE only when this criterion exposes a concrete
gap; otherwise choose RETAIN. Keep each field to one short sentence. Cite only an allowed
evidence ID. Never invent or modify a vendor, SKU, URL, dimension, load, price, certification,
availability, safety conclusion, or fabrication-release claim. Existing geometry is product-
concept CAD and remains behind human engineering gates. Do not copy proprietary styling.

Fixed family constraints:
{family_constraints}

Current module evidence:
{module_lines}

Allowed evidence IDs:
{evidence_lines}

{prior_block}
Return JSON only with exactly this shape and all ten IDs once:
{{"cycle_id":"{stage}-{cycle:02d}","reviews":[{{"module_id":"BN-M01",
"verdict":"REVISE or RETAIN","proposal":"specific change or explicit retain statement",
"rationale":"why for this criterion","evidence_ids":["one or more allowed IDs"],
"acceptance_check":"observable or deterministic check","risk":"remaining risk or none"}}]}}

Hard length limits, counted in characters after trimming. Output that exceeds
them is rejected, so keep every field to one short sentence:
- proposal: {proposal_min}-{proposal_max}
- rationale: {rationale_min}-{rationale_max}
- acceptance_check: {acceptance_min}-{acceptance_max}
- risk: {risk_min}-{risk_max}
- evidence_ids: 1-4 distinct IDs from the allowed list above
""".format(
        cycle=cycle, stage=stage, criterion_name=criterion["criterion"],
        question=criterion["question"],
        family_constraints=json.dumps(context["family_constraints"], sort_keys=True),
        module_lines="\n".join(module_lines),
        evidence_lines="\n".join(evidence_lines),
        prior_block=("Prior accepted requirements (avoid repetition):\n" +
                     "\n".join(prior_lines)) if prior_lines else "No prior requirements in this run.",
        proposal_min=FIELD_LIMITS["proposal"][0], proposal_max=FIELD_LIMITS["proposal"][1],
        rationale_min=FIELD_LIMITS["rationale"][0], rationale_max=FIELD_LIMITS["rationale"][1],
        acceptance_min=FIELD_LIMITS["acceptance_check"][0],
        acceptance_max=FIELD_LIMITS["acceptance_check"][1],
        risk_min=FIELD_LIMITS["risk"][0], risk_max=FIELD_LIMITS["risk"][1],
    )


def validate_review_text(field, value, minimum, maximum, failures, module_id):
    if not isinstance(value, str):
        failures.append("%s %s must be a string, got %s" %
                        (module_id, field, type(value).__name__))
        return
    length = len(value.strip())
    if not minimum <= length <= maximum:
        # State the measured length and the bound. A bare "invalid" gives the
        # model nothing to act on, so its repair attempt resamples instead of
        # shortening, and a whole multi-cycle run dies on one long sentence.
        failures.append(
            "%s %s is %d characters; rewrite it to between %d and %d characters "
            "(shorten by at least %d)" %
            (module_id, field, length, minimum, maximum, max(1, length - maximum))
            if length > maximum else
            "%s %s is %d characters; expand it to between %d and %d characters" %
            (module_id, field, length, minimum, maximum)
        )
        return
    if URL_RE.search(value):
        failures.append("%s %s contains a model-authored URL" % (module_id, field))
    if UNSOURCED_CLAIM_RE.search(value):
        failures.append("%s %s contains a prohibited release/compliance claim" %
                        (module_id, field))


def validate_cycle(value, expected_id, stage, context, comparable, catalog):
    failures = []
    if not isinstance(value, dict) or set(value) != {"cycle_id", "reviews"}:
        return ["top-level object must contain only cycle_id and reviews"]
    if value["cycle_id"] != expected_id:
        failures.append("cycle_id must be %s" % expected_id)
    reviews = value.get("reviews")
    if not isinstance(reviews, list) or len(reviews) != 10:
        return failures + ["reviews must contain exactly ten objects"]
    module_by_id, comp_by_module, catalog_by_id = source_maps(context, comparable, catalog)
    seen = []
    expected_fields = {"module_id", "verdict", "proposal", "rationale",
                       "evidence_ids", "acceptance_check", "risk"}
    for review in reviews:
        if not isinstance(review, dict):
            failures.append("review is not an object")
            continue
        module_id = review.get("module_id", "UNKNOWN")
        seen.append(module_id)
        if set(review) != expected_fields:
            failures.append("%s fields differ from schema" % module_id)
        if module_id not in module_by_id:
            failures.append("unknown module_id %s" % module_id)
            continue
        if review.get("verdict") not in ("REVISE", "RETAIN"):
            failures.append("%s verdict invalid" % module_id)
        for field, (low, high) in FIELD_LIMITS.items():
            validate_review_text(field, review.get(field), low, high, failures, module_id)
        ids = review.get("evidence_ids")
        allowed = evidence_for(stage, module_by_id[module_id], comp_by_module, catalog_by_id)
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 4 or
                len(ids) != len(set(ids)) or any(item not in allowed for item in ids)):
            failures.append("%s evidence_ids are missing, repeated, or not allowed" % module_id)
    if sorted(seen) != MODULE_IDS:
        failures.append("reviews must contain every module exactly once")
    return failures


def repair_prompt(raw, failures, expected_id):
    return """Repair the JSON below. Return JSON only. Preserve the engineering meaning but fix
every listed validation failure. The cycle_id is {expected_id}; include every BN-M01 through
BN-M10 exactly once and no extra fields. Do not add URLs, claims, SKUs, or evidence IDs.
Failures:
- {failures}
Invalid output:
{raw}
""".format(expected_id=expected_id, failures="\n- ".join(failures), raw=raw)


def run_cycle(base_url, model, stage, cycle, criterion, context, comparable,
              catalog, prior, output_dir, force=False, attempts=DEFAULT_ATTEMPTS,
              max_tokens=2000, cooldown_seconds=0, allowed_models=None,
              resource_guard=None):
    cycle_id = "%s-%02d" % (stage, cycle)
    validated_path = output_dir / stage / (cycle_id + ".validated.json")
    if validated_path.is_file() and not force:
        existing = read_json(validated_path)
        if existing.get("model") not in (allowed_models or {model}):
            raise CycleError(
                "%s was proposed by %r, which is outside this run's approved model policy %s" %
                (cycle_id, existing.get("model"), sorted(allowed_models or {model}))
            )
        failures = validate_cycle(existing["model_output"], cycle_id, stage,
                                  context, comparable, catalog)
        if not failures:
            print("%s RESUME_PASS" % cycle_id, flush=True)
            return existing
    prompt = prompt_for(stage, cycle, criterion, context, comparable, catalog, prior)
    system = ("You are a conservative product-design and manufacturing reviewer. "
              "Follow the JSON contract exactly and abstain from unsourced claims.")
    raw_records = []
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": prompt}]
    final_value = None
    final_failures = []
    total_usage = {}
    for attempt in range(1, attempts + 1):
        raw, usage = call_model(
            base_url, model, messages, max_tokens=max_tokens,
            resource_guard=resource_guard
        )
        raw_path = output_dir / stage / ("%s.attempt-%d.raw.txt" % (cycle_id, attempt))
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw)
        raw_records.append({"attempt": attempt, "path": str(raw_path),
                            "sha256": digest_bytes(raw.encode()), "usage": usage})
        total_usage = usage
        try:
            value = extract_json(raw)
            failures = validate_cycle(value, cycle_id, stage, context, comparable, catalog)
        except Exception as exc:
            value, failures = None, ["JSON parse error: %s" % exc]
        if not failures:
            final_value = value
            break
        final_failures = failures
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": repair_prompt(raw, failures, cycle_id)})
        if cooldown_seconds > 0:
            print("%s RETRY_COOLDOWN %.1fs" % (cycle_id, cooldown_seconds), flush=True)
            time.sleep(cooldown_seconds)
    if final_value is None:
        raise CycleError("%s failed after %d attempts: %s" %
                         (cycle_id, attempts, "; ".join(final_failures)))
    record = {
        "schema_version": 1,
        "cycle_id": cycle_id,
        "stage": stage,
        "cycle": cycle,
        "criterion": criterion,
        "model": model,
        "endpoint": base_url,
        "completed_at": now(),
        "prompt_sha256": digest_bytes(prompt.encode()),
        "source_digests": {
            "context": canonical_digest(context),
            "comparables": canonical_digest(comparable),
            "catalog": canonical_digest(catalog)
        },
        "attempts": raw_records,
        "usage": total_usage,
        "validation": {"result": "PASS", "failures": []},
        "model_output": final_value,
        "authority": "advisory local-model proposal; adopted requirements remain prototype-only and human-gated"
    }
    write_json(validated_path, record)
    revised = sum(item["verdict"] == "REVISE" for item in final_value["reviews"])
    print("%s PASS revised=%d retained=%d" % (cycle_id, revised, 10 - revised), flush=True)
    if cooldown_seconds > 0:
        print("%s COOLDOWN %.1fs" % (cycle_id, cooldown_seconds), flush=True)
        time.sleep(cooldown_seconds)
    return record


def select_stages(value):
    return STAGES if value == "all" else (value,)


def load_prior_reviews(output_dir):
    reviews = []
    for stage in STAGES:
        for cycle in range(1, 11):
            path = output_dir / stage / ("%s-%02d.validated.json" % (stage, cycle))
            if path.is_file():
                try:
                    reviews.extend(read_json(path)["model_output"]["reviews"])
                except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                    continue
    return reviews


def rebuild_ledger(output_dir, model, allowed_models, context, comparable, catalog):
    records = []
    failures = []
    for stage in STAGES:
        for cycle in range(1, 11):
            cycle_id = "%s-%02d" % (stage, cycle)
            path = output_dir / stage / (cycle_id + ".validated.json")
            if not path.is_file():
                continue
            record = read_json(path)
            record_failures = validate_cycle(record.get("model_output"), cycle_id, stage,
                                              context, comparable, catalog)
            if record.get("model") not in allowed_models:
                record_failures.append("model is outside the approved model policy")
            if record_failures:
                failures.extend("%s: %s" % (cycle_id, item) for item in record_failures)
                continue
            for review in record["model_output"]["reviews"]:
                records.append({
                    "record_id": "%s-%s" % (cycle_id, review["module_id"]),
                    "cycle_id": cycle_id,
                    "stage": stage,
                    "cycle": cycle,
                    "criterion": record["criterion"]["criterion"],
                    "module_id": review["module_id"],
                    "verdict": review["verdict"],
                    "gate_decision": ("ADOPT_AS_PROTOTYPE_REQUIREMENT" if
                                      review["verdict"] == "REVISE" else
                                      "RETAIN_VALIDATED_BASELINE"),
                    "proposal": review["proposal"],
                    "rationale": review["rationale"],
                    "evidence_ids": review["evidence_ids"],
                    "acceptance_check": review["acceptance_check"],
                    "risk": review["risk"],
                    "model": record["model"],
                    "record_sha256": canonical_digest(review)
                })
    expected = 300
    complete = len(records) == expected and not failures
    model_counts = {
        item: sum(record.get("model") == item for record in records)
        for item in sorted(allowed_models)
    }
    mixed = len([count for count in model_counts.values() if count]) > 1
    ledger = {
        "schema_version": 1,
        "result": "PASS" if complete else "INCOMPLETE",
        "generated_at": now(),
        "required_model": PRIMARY_MODEL,
        "active_model": model,
        "allowed_models": sorted(allowed_models),
        "model_counts": model_counts,
        "model_policy": {
            "mode": "documented_low_memory_continuation" if mixed else "single_model",
            "primary_model": PRIMARY_MODEL,
            "low_memory_model": LOW_MEMORY_MODEL,
            "reason": (
                "The 16 GB M1 Pro laptop recorded repeated IOGPUFamily kernel panics "
                "while the 14B MLX model used an estimated 10.86 GiB. Validated 14B "
                "cycles were preserved and remaining cycles used the installed 7B "
                "MLX coder at an estimated 5.60 GiB. The Mac mini profile keeps 14B."
                if mixed else "All accepted records use one approved local coding model."
            )
        },
        "cycle_count": len({item["cycle_id"] for item in records}),
        "module_review_count": len(records),
        "expected_module_review_count": expected,
        "counts": {
            "revisions_adopted": sum(item["gate_decision"] ==
                                     "ADOPT_AS_PROTOTYPE_REQUIREMENT" for item in records),
            "baseline_retained": sum(item["gate_decision"] ==
                                     "RETAIN_VALIDATED_BASELINE" for item in records)
        },
        "failures": failures,
        "records": records,
        "learning_persistence": "Weights are unchanged. Validated learnings persist in this ledger and are injected into subsequent prompts and the Mac mini replication framework.",
        "release_authority": "No automated review can authorize fabrication, purchase, vehicle installation, or sale."
    }
    write_json(output_dir / "iteration-ledger.json", ledger)
    for stage_index, stage in enumerate(STAGES, 1):
        allowed_stages = set(STAGES[:stage_index])
        stage_records = [item for item in records if item["stage"] in allowed_stages]
        stage_expected = stage_index * 100
        snapshot = dict(ledger)
        snapshot["result"] = ("PASS" if len(stage_records) == stage_expected and
                              not failures else "INCOMPLETE")
        snapshot["through_stage"] = stage
        snapshot["cycle_count"] = len({item["cycle_id"] for item in stage_records})
        snapshot["module_review_count"] = len(stage_records)
        snapshot["expected_module_review_count"] = stage_expected
        snapshot["counts"] = {
            "revisions_adopted": sum(
                item["gate_decision"] == "ADOPT_AS_PROTOTYPE_REQUIREMENT"
                for item in stage_records
            ),
            "baseline_retained": sum(
                item["gate_decision"] == "RETAIN_VALIDATED_BASELINE"
                for item in stage_records
            ),
        }
        snapshot["records"] = stage_records
        write_json(output_dir / (stage + "-ledger.json"), snapshot)
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES + ("all",), default="all")
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS,
                        help="model attempts per cycle before the run aborts")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--allow-model", action="append", default=[],
                        help="additional model ID whose existing validated cycles may be resumed")
    parser.add_argument("--max-tokens", type=int,
                        default=int(os.environ.get("BN_REVISION_MAX_TOKENS", "2000")))
    parser.add_argument("--cooldown-seconds", type=float,
                        default=float(os.environ.get("BN_REVISION_COOLDOWN_SECONDS", "0")))
    parser.add_argument("--max-load", type=float,
                        default=float(os.environ.get(
                            "BN_REVISION_MAX_LOAD", str(max(12, (os.cpu_count() or 4) * 2))
                        )))
    parser.add_argument("--min-free-percent", type=int,
                        default=int(os.environ.get("BN_REVISION_MIN_FREE_PERCENT", "20")))
    parser.add_argument("--guard-poll-seconds", type=float, default=15)
    parser.add_argument("--guard-timeout-seconds", type=float, default=3600)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--output-dir", type=pathlib.Path, default=HERE / "runs")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--guard-only", action="store_true",
                        help="wait for the configured resource floor, then exit")
    args = parser.parse_args()
    if args.start < 1 or args.count < 1 or args.start + args.count - 1 > 10:
        parser.error("--start/--count must select cycles within 1..10")
    if args.max_tokens < 256 or args.cooldown_seconds < 0:
        parser.error("--max-tokens must be >= 256 and cooldown must be >= 0")
    env_allowed = [item.strip() for item in
                   os.environ.get("BN_ALLOWED_REVIEW_MODELS", "").split(",")
                   if item.strip()]
    allowed_models = set([args.model] + args.allow_model + env_allowed)
    if not allowed_models <= APPROVED_MODELS:
        parser.error("approved model policy permits only: %s" %
                     ", ".join(sorted(APPROVED_MODELS)))
    if args.guard_only:
        wait_for_resources(
            args.max_load, args.min_free_percent, args.guard_poll_seconds,
            args.guard_timeout_seconds
        )
        print("RESOURCE_GUARD_READY")
        return 0
    context = read_json(HERE / "module-review-context.json")
    comparable = read_json(HERE / "comparable-products.json")
    catalog = read_json(HERE / "ots-components.json")
    criteria = read_json(HERE / "review-criteria.json")
    if not args.validate_only:
        visible = lm_models(args.endpoint)
        if args.model not in visible:
            raise CycleError("required model %r is not visible at %s" %
                             (args.model, args.endpoint))
        prior = load_prior_reviews(args.output_dir)
        resource_guard = {
            "max_load": args.max_load,
            "min_free_percent": args.min_free_percent,
            "poll_seconds": args.guard_poll_seconds,
            "timeout_seconds": args.guard_timeout_seconds,
        }
        for stage in select_stages(args.stage):
            for cycle in range(args.start, args.start + args.count):
                record = run_cycle(
                    args.endpoint, args.model, stage, cycle,
                    criteria["stages"][stage][cycle - 1], context, comparable,
                    catalog, prior, args.output_dir, args.force, args.attempts,
                    args.max_tokens, args.cooldown_seconds, allowed_models,
                    resource_guard
                )
                prior.extend(record["model_output"]["reviews"])
    ledger = rebuild_ledger(
        args.output_dir, args.model, allowed_models, context, comparable, catalog
    )
    print("REVISION_LEDGER_%s cycles=%d reviews=%d path=%s" %
          (ledger["result"], ledger["cycle_count"],
           ledger["module_review_count"], args.output_dir / "iteration-ledger.json"))
    return 0 if (ledger["result"] == "PASS" or args.stage != "all" or
                 args.count != 10) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CycleError, urllib.error.URLError) as exc:
        print("REVISION_CYCLE_FAIL %s" % exc, file=sys.stderr)
        raise SystemExit(1)
