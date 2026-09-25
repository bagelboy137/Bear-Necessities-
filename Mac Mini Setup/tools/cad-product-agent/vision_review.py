#!/usr/bin/env python3
"""Advisory-but-blocking local VLM review of the Fusion candidate screenshot."""

import argparse
import base64
import json
import os
import pathlib
import re
import urllib.request


def extract_json(text):
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    candidate = match.group(1) if match else text
    return json.loads(candidate.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job = json.loads(pathlib.Path(args.job).read_text())
    image_path = pathlib.Path(args.image)
    if not image_path.is_file():
        print(f"VISUAL QA FAILED: screenshot missing: {image_path}")
        return 1
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    prompt = f'''Independently inspect this Fusion CAD screenshot for job {job['job_id']} revision {job['revision']}.
Expected bounding box: {job['expected'].get('bbox')}. Expected solid count: {job['expected'].get('solid_count')}.
Look only for visible omissions, duplicated members, impossible intersections, asymmetry, orientation errors, missing holes/features, or a clearly unusable camera/view. Do not infer dimensions, structural adequacy, tolerances, or fabrication readiness from pixels.
Return JSON only: {{"verdict":"VISUAL_QA_PASS" or "VISUAL_QA_FLAGGED", "job_id":"...", "findings":[{{"severity":"blocking|warning", "description":"..."}}], "limitations":["..."]}}.'''
    payload = {
        "model": args.model, "temperature": 0, "max_tokens": 800,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}},
        ]}],
    }
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LM_API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["LM_API_TOKEN"]
    request = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions",
                                     data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            content = json.load(response)["choices"][0]["message"]["content"]
        result = extract_json(content)
    except Exception as exc:
        print(f"VISUAL QA FAILED: {exc}")
        return 1
    if result.get("job_id") != job["job_id"]:
        print("VISUAL QA FAILED: response job_id mismatch")
        return 1
    result["model"] = args.model
    result["image_sha256"] = __import__("hashlib").sha256(image_path.read_bytes()).hexdigest()
    pathlib.Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(f"VISUAL QA {result.get('verdict')}: {args.output}")
    return 0 if result.get("verdict") == "VISUAL_QA_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
