from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SERVICE_ARN = re.compile(
    r"^arn:(?P<partition>aws(?:-[a-z0-9-]+)?):apprunner:(?P<region>[a-z0-9-]+):(?P<account>[0-9]{12}):service/(?P<name>[A-Za-z0-9][A-Za-z0-9-_]{3,39})/(?P<id>[A-Za-z0-9]{32})$"
)


def app_runner_log_groups(service_arn: str) -> tuple[str, str]:
    """Return the AWS-documented App Runner service/application log groups."""
    match = _SERVICE_ARN.fullmatch(service_arn)
    if not match:
        raise ValueError("service_arn is not a valid App Runner service ARN")
    prefix = f"/aws/apprunner/{match.group('name')}/{match.group('id')}"
    return f"{prefix}/service", f"{prefix}/application"


def _embedded_json(message: str) -> dict[str, Any] | None:
    """Extract a JSON object from a raw CloudWatch log message if one is present."""
    start = message.find("{")
    if start < 0:
        return None
    try:
        value = json.loads(message[start:])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _events(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError(f"{label} capture must contain an events list")
    return [event for event in events if isinstance(event, dict)]


def build_observability_evidence(
    deployment_evidence: dict[str, Any],
    service_logs: dict[str, Any],
    application_logs: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless CloudWatch proves App Runner lifecycle + QC/EMF telemetry."""
    record = copy.deepcopy(deployment_evidence)
    source_sha = str(record.get("source_git_sha", "")).lower()
    aws = record.get("aws")
    if not isinstance(aws, dict):
        raise ValueError("deployment evidence must contain aws metadata")

    service_arn = str(aws.get("service_arn", ""))
    service_group, application_group = app_runner_log_groups(service_arn)
    service_events = _events(service_logs, "service log")
    application_events = _events(application_logs, "application log")
    if not service_events:
        raise ValueError("CloudWatch service log capture contains no events")
    if not application_events:
        raise ValueError("CloudWatch application log capture contains no events")

    messages = [str(event.get("message", "")) for event in application_events]
    if any("image_base64" in message or "data:image/" in message for message in messages):
        raise ValueError("application logs contain raw-image payload markers")

    objects = [obj for message in messages if (obj := _embedded_json(message)) is not None]
    qc_events = [
        obj
        for obj in objects
        if obj.get("event") == "qc_decision"
        and str(obj.get("build_sha", "")).lower() == source_sha
        and str(obj.get("opencv", "")) == "5.0.0"
    ]
    emf_events = [
        obj
        for obj in objects
        if obj.get("Service") == "hal-labsight"
        and str(obj.get("build_sha", "")).lower() == source_sha
        and str(obj.get("opencv", "")) == "5.0.0"
        and isinstance(obj.get("_aws"), dict)
        and any(
            metric.get("Namespace") == "HAL/LabSight"
            for metric in obj["_aws"].get("CloudWatchMetrics", [])
            if isinstance(metric, dict)
        )
    ]
    if not qc_events:
        raise ValueError("CloudWatch application logs do not prove source-bound OpenCV 5 QC decisions")
    if not emf_events:
        raise ValueError("CloudWatch application logs do not contain HAL/LabSight EMF metrics")

    timestamps = [
        int(event["timestamp"])
        for event in service_events + application_events
        if isinstance(event.get("timestamp"), (int, float))
    ]
    aws["cloudwatch_evidence"] = True
    aws["cloudwatch"] = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "service_log_group": service_group,
        "application_log_group": application_group,
        "service_event_count": len(service_events),
        "application_event_count": len(application_events),
        "source_bound_qc_event_count": len(qc_events),
        "emf_event_count": len(emf_events),
        "raw_image_payload_markers_detected": False,
        "first_event_timestamp_ms": min(timestamps) if timestamps else None,
        "last_event_timestamp_ms": max(timestamps) if timestamps else None,
    }
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate App Runner CloudWatch logs and enrich LabSight AWS evidence"
    )
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--service-logs", type=Path, required=True)
    parser.add_argument("--application-logs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    record = build_observability_evidence(
        json.loads(args.deployment.read_text(encoding="utf-8")),
        json.loads(args.service_logs.read_text(encoding="utf-8")),
        json.loads(args.application_logs.read_text(encoding="utf-8")),
    )
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
