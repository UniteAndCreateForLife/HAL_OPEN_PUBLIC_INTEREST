import json

import pytest

from tools.aws_observability_evidence import (
    app_runner_log_groups,
    build_observability_evidence,
)


SOURCE_SHA = "a" * 40
SERVICE_ARN = (
    "arn:aws:apprunner:us-east-1:123456789012:service/"
    "hal-labsight/1234567890abcdef1234567890abcdef"
)


def _deployment() -> dict:
    return {
        "source_git_sha": SOURCE_SHA,
        "aws": {
            "service_arn": SERVICE_ARN,
            "cloudwatch_evidence": False,
        },
    }


def _service_logs() -> dict:
    return {"events": [{"timestamp": 1000, "message": "[AppRunner] Service started"}]}


def _application_logs(*, include_qc: bool = True, include_emf: bool = True) -> dict:
    messages = []
    if include_qc:
        messages.append(
            {
                "event": "qc_decision",
                "build_sha": SOURCE_SHA,
                "opencv": "5.0.0",
                "decision": "accept",
            }
        )
    if include_emf:
        messages.append(
            {
                "_aws": {
                    "CloudWatchMetrics": [
                        {
                            "Namespace": "HAL/LabSight",
                            "Dimensions": [["Service", "Decision", "SourceClass"]],
                        }
                    ]
                },
                "Service": "hal-labsight",
                "Decision": "accept",
                "build_sha": SOURCE_SHA,
                "opencv": "5.0.0",
            }
        )
    return {
        "events": [
            {"timestamp": 2000 + index, "message": "INFO:labsight.metrics:" + json.dumps(message)}
            for index, message in enumerate(messages)
        ]
    }


def test_app_runner_log_groups_follow_documented_naming():
    assert app_runner_log_groups(SERVICE_ARN) == (
        "/aws/apprunner/hal-labsight/1234567890abcdef1234567890abcdef/service",
        "/aws/apprunner/hal-labsight/1234567890abcdef1234567890abcdef/application",
    )


def test_cloudwatch_evidence_requires_source_bound_qc_and_emf():
    record = build_observability_evidence(
        _deployment(), _service_logs(), _application_logs()
    )
    cloudwatch = record["aws"]["cloudwatch"]
    assert record["aws"]["cloudwatch_evidence"] is True
    assert cloudwatch["service_event_count"] == 1
    assert cloudwatch["source_bound_qc_event_count"] == 1
    assert cloudwatch["emf_event_count"] == 1
    assert cloudwatch["raw_image_payload_markers_detected"] is False


def test_cloudwatch_evidence_rejects_missing_emf():
    with pytest.raises(ValueError, match="EMF metrics"):
        build_observability_evidence(
            _deployment(), _service_logs(), _application_logs(include_emf=False)
        )


def test_cloudwatch_evidence_rejects_wrong_source_sha():
    logs = _application_logs()
    logs["events"][0]["message"] = logs["events"][0]["message"].replace(SOURCE_SHA, "b" * 40)
    with pytest.raises(ValueError, match="source-bound"):
        build_observability_evidence(_deployment(), _service_logs(), logs)


def test_cloudwatch_evidence_rejects_raw_image_payload_markers():
    logs = _application_logs()
    logs["events"].append({"timestamp": 3000, "message": '{"image_base64":"abc"}'})
    with pytest.raises(ValueError, match="raw-image payload"):
        build_observability_evidence(_deployment(), _service_logs(), logs)


def test_cloudwatch_evidence_rejects_wrong_emf_source_sha():
    logs = _application_logs()
    logs["events"][1]["message"] = logs["events"][1]["message"].replace(SOURCE_SHA, "b" * 40)
    with pytest.raises(ValueError, match="EMF metrics"):
        build_observability_evidence(_deployment(), _service_logs(), logs)
