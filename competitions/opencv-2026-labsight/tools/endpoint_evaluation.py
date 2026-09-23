from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

EXPECTED_OPENCV_DISTRIBUTION = "5.0.0.93"
EXPECTED_OPENCV_RUNTIME = "5.0.0"

Transport = Callable[
    [str, str, dict[str, Any] | None, float],
    tuple[dict[str, Any], dict[str, str], float],
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_base_url(value: str) -> str:
    value = value.rstrip("/")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def http_json_transport(
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, str], float]:
    data = None
    headers = {"accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["content-type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
        response_headers = {key.lower(): value for key, value in response.headers.items()}
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if not isinstance(body, dict):
        raise ValueError(f"{url} did not return a JSON object")
    return body, response_headers, elapsed_ms


def verify_health(health: dict[str, Any], expected_sha: str) -> None:
    if str(health.get("source_sha", "")).lower() != expected_sha.lower():
        raise ValueError("remote /health source_sha does not match expected source SHA")
    if (
        health.get("opencv_distribution_version") != EXPECTED_OPENCV_DISTRIBUTION
        or health.get("opencv_runtime_version") != EXPECTED_OPENCV_RUNTIME
        or health.get("opencv5_verified") is not True
    ):
        raise ValueError("remote endpoint does not prove the exact OpenCV 5 competition runtime")


def _accuracy(rows: list[dict[str, Any]], key: str) -> float | None:
    scored = [row[key] for row in rows if row[key] is not None]
    if not scored:
        return None
    return sum(bool(value) for value in scored) / len(scored)


def evaluate_endpoint(
    base_url: str,
    expected_sha: str,
    manifest_path: Path,
    *,
    timeout: float = 30.0,
    transport: Transport = http_json_transport,
) -> dict[str, Any]:
    base_url = _normalize_base_url(base_url)
    health, _, health_ms = transport("GET", f"{base_url}/health", None, timeout)
    verify_health(health, expected_sha)

    judge, _, judge_ms = transport("GET", f"{base_url}/demo/judge", None, timeout)
    judge_ok = (
        judge.get("all_expectations_met") is True
        and (judge.get("agentic_vision") or {}).get("opencv_observation_changes_next_action") is True
        and (judge.get("responsible_use") or {}).get("diagnostic_claims") is False
    )
    if not judge_ok:
        raise ValueError("remote judge suite did not prove expected Agentic Vision behavior")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("purpose") != "image_quality_control_only" or manifest.get("diagnostic_claims") is not False:
        raise ValueError("manifest must be explicitly limited to image-quality control")
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("manifest must contain at least one item")

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("manifest items must be JSON objects")
        image_path = manifest_path.parent / str(item.get("path", ""))
        if not image_path.is_file():
            raise ValueError(f"manifest image is missing: {image_path}")
        expected_digest = str(item.get("sha256", "")).lower()
        actual_digest = _sha256(image_path)
        if actual_digest != expected_digest:
            raise ValueError(f"manifest SHA-256 mismatch for {item.get('id')}")

        payload = {"image_base64": base64.b64encode(image_path.read_bytes()).decode("ascii")}
        result, headers, elapsed_ms = transport("POST", f"{base_url}/analyze", payload, timeout)
        latencies.append(elapsed_ms)
        trace = result.get("trace") or []
        first_action = trace[0].get("decision") if trace and isinstance(trace[0], dict) else None
        final_action = result.get("status")
        used_enhancement = bool(result.get("used_enhancement"))

        expected_final = item.get("expected_qc_status")
        expected_first = item.get("expected_first_action")
        expected_enhancement = item.get("expected_enhancement")
        final_correct = None if expected_final is None else final_action == expected_final
        first_correct = None if expected_first is None else first_action == expected_first
        enhancement_correct = (
            None if expected_enhancement is None else used_enhancement is expected_enhancement
        )
        unsafe_accept = expected_final in {
            "request_recapture_focus",
            "request_recapture_exposure",
            "human_review",
        } and final_action == "accept"

        rows.append({
            "id": item.get("id"),
            "derivation": item.get("derivation"),
            "sha256": actual_digest,
            "expected_final_action": expected_final,
            "observed_final_action": final_action,
            "final_correct": final_correct,
            "expected_first_action": expected_first,
            "observed_first_action": first_action,
            "first_correct": first_correct,
            "expected_enhancement": expected_enhancement,
            "observed_enhancement": used_enhancement,
            "enhancement_correct": enhancement_correct,
            "unsafe_accept": unsafe_accept,
            "trace_steps": len(trace),
            "round_trip_ms": round(elapsed_ms, 3),
            "request_id": headers.get("x-labsight-request-id"),
            "server_timing": headers.get("server-timing"),
        })

    scored_rows = [
        row
        for row in rows
        if row["final_correct"] is not None
        or row["first_correct"] is not None
        or row["enhancement_correct"] is not None
    ]
    unsafe_accepts = sum(bool(row["unsafe_accept"]) for row in rows)
    all_scored_expectations_met = all(
        value is not False
        for row in scored_rows
        for value in (
            row["final_correct"],
            row["first_correct"],
            row["enhancement_correct"],
        )
    )
    sorted_latency = sorted(latencies)
    p95_index = min(len(sorted_latency) - 1, max(0, int(len(sorted_latency) * 0.95) - 1))
    verified = judge_ok and all_scored_expectations_met and unsafe_accepts == 0

    return {
        "schema_version": "1.0",
        "evidence_scope": "live_endpoint_evaluation_not_aws_identity_by_itself",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": base_url,
        "source_git_sha": expected_sha.lower(),
        "health": health,
        "judge_suite": {
            "all_expectations_met": True,
            "agentic_vision_proved": True,
            "round_trip_ms": round(judge_ms, 3),
        },
        "corpus": {
            "dataset": manifest.get("dataset"),
            "manifest_path": manifest_path.as_posix(),
            "manifest_sha256": _sha256(manifest_path),
            "items": len(rows),
            "scored_items": len(scored_rows),
            "provenance_source_locks": len(manifest.get("source_locks") or []),
        },
        "scores": {
            "final_action_accuracy": _accuracy(rows, "final_correct"),
            "first_action_accuracy": _accuracy(rows, "first_correct"),
            "enhancement_accuracy": _accuracy(rows, "enhancement_correct"),
            "unsafe_accepts": unsafe_accepts,
            "all_scored_expectations_met": all_scored_expectations_met,
        },
        "latency_ms": {
            "health": round(health_ms, 3),
            "mean": round(statistics.mean(latencies), 3),
            "median": round(statistics.median(latencies), 3),
            "p95": round(sorted_latency[p95_index], 3),
            "max": round(max(latencies), 3),
        },
        "readiness_fragment": {
            "evaluation": {
                "deployed_endpoint_verified": verified,
                "deployed_source_sha": expected_sha.lower(),
                "deployed_judge_suite_passed": judge_ok,
                "deployed_real_corpus_scored": len(scored_rows),
                "deployed_unsafe_accepts": unsafe_accepts,
            }
        },
        "responsible_use": {
            "microscopy_qc_only": True,
            "diagnostic_claims": False,
        },
        "samples": rows,
    }


def enrich_deployment_evidence(
    deployment: dict[str, Any],
    endpoint_record: dict[str, Any],
) -> dict[str, Any]:
    source_sha = str(deployment.get("source_git_sha", "")).lower()
    if source_sha != str(endpoint_record.get("source_git_sha", "")).lower():
        raise ValueError("endpoint evaluation source SHA does not match deployment evidence")
    aws = deployment.get("aws") or {}
    deployment_url = _normalize_base_url(str(aws.get("app_runner_url", "")))
    if deployment_url != _normalize_base_url(str(endpoint_record.get("endpoint", ""))):
        raise ValueError("endpoint evaluation URL does not match deployment evidence")

    record = copy.deepcopy(deployment)
    evaluation = record.setdefault("evaluation", {})
    if not isinstance(evaluation, dict):
        raise ValueError("deployment evaluation field must be a JSON object")
    fragment = (endpoint_record.get("readiness_fragment") or {}).get("evaluation")
    if not isinstance(fragment, dict):
        raise ValueError("endpoint evaluation does not contain a readiness fragment")
    evaluation.update(fragment)
    evaluation["deployed_endpoint_report"] = {
        "scope": endpoint_record.get("evidence_scope"),
        "captured_at_utc": endpoint_record.get("captured_at_utc"),
        "corpus": endpoint_record.get("corpus"),
        "scores": endpoint_record.get("scores"),
        "latency_ms": endpoint_record.get("latency_ms"),
    }
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a live LabSight endpoint against judge and frozen real-image evidence"
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--deployment-evidence", type=Path)
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args(argv)
    if bool(args.deployment_evidence) != bool(args.evidence_output):
        parser.error("--deployment-evidence and --evidence-output must be used together")

    record = evaluate_endpoint(
        args.base_url,
        args.source_sha,
        args.manifest,
        timeout=args.timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    if args.deployment_evidence and args.evidence_output:
        deployment = json.loads(args.deployment_evidence.read_text(encoding="utf-8"))
        enriched = enrich_deployment_evidence(deployment, record)
        args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_output.write_text(
            json.dumps(enriched, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(rendered, end="")
    return 0 if record["readiness_fragment"]["evaluation"]["deployed_endpoint_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
