"""Probe real HTTP in the serving container; this is not AWS evidence."""
from __future__ import annotations

import argparse
import json
import re
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from labsight.runtime import EXPECTED_CV2_VERSION, EXPECTED_OPENCV_DISTRIBUTION

EXPECTED = {
    "clean": ("accept", False),
    "blurred": ("request_recapture_focus", False),
    "uneven": ("accept", True),
    "clipped": ("request_recapture_exposure", False),
}


def validate_capture(source_sha: str, health: dict, scenarios: dict) -> dict:
    """Fail closed on wrong source, runtime, decision, or agent control flow."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("source_sha must be a full lowercase Git SHA")
    if any(health.get(key) != source_sha for key in ("source_sha", "build_sha")):
        raise ValueError("health source/build SHA mismatch")
    if health.get("opencv_distribution_version") != EXPECTED_OPENCV_DISTRIBUTION:
        raise ValueError("wrong OpenCV distribution")
    if health.get("opencv_runtime_version") != EXPECTED_CV2_VERSION:
        raise ValueError("wrong OpenCV core runtime")
    if health.get("opencv5_verified") is not True or health.get("status") != "ok":
        raise ValueError("runtime health is not verified")
    if set(scenarios) != set(EXPECTED):
        raise ValueError("all four QC scenarios must be observed")
    for name, (status, enhancement) in EXPECTED.items():
        row = scenarios[name]
        trace = row.get("trace", [])
        expected_decisions = ["enhance_and_reanalyze", status] if enhancement else [status]
        if row.get("status") != status or row.get("used_enhancement") is not enhancement:
            raise ValueError(f"{name}: wrong QC outcome or enhancement use")
        if [step.get("decision") for step in trace] != expected_decisions:
            raise ValueError(f"{name}: wrong perception/action trace")
        if any(not step.get("observation") for step in trace):
            raise ValueError(f"{name}: missing visual observations")
    return {
        "schema_version": 1,
        "scope": "local/CI container HTTP canary; NOT AWS deployment evidence",
        "purpose": "image_quality_control_only",
        "diagnostic_claims": False,
        "aws_deployed": False,
        "source_sha": source_sha,
        "passed": True,
        "health": health,
        "scenarios": scenarios,
    }

def read_json(path: str, request_id: str) -> dict:
    request = Request("http://127.0.0.1:8080" + path, headers={"x-request-id": request_id})
    with urlopen(request, timeout=5) as response:
        if response.headers.get("x-labsight-request-id") != request_id:
            raise ValueError("HTTP request correlation failed")
        if not response.headers.get("server-timing", "").startswith("labsight;dur="):
            raise ValueError("HTTP latency evidence is missing")
        return json.load(response)


def probe(source_sha: str) -> dict:
    health = None
    for attempt in range(30):
        try:
            health = read_json("/health", "container-health")
            break
        except (URLError, TimeoutError):
            if attempt == 29:
                raise
            time.sleep(0.5)
    scenarios = {name: read_json("/demo/analyze/" + name, "container-" + name) for name in EXPECTED}
    return validate_capture(source_sha, health, scenarios)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    print(json.dumps(probe(parser.parse_args().source_sha), indent=2, sort_keys=True))
