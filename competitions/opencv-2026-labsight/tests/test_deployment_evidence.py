import json

import pytest

from tools.deployment_evidence import (
    EXPECTED_OPENCV_DISTRIBUTION,
    EXPECTED_OPENCV_RUNTIME,
    build_deployment_evidence,
)


def _health(source_sha: str) -> dict:
    return {
        "status": "ok",
        "service": "hal-labsight",
        "build_sha": source_sha,
        "source_sha": source_sha,
        "opencv_distribution_version": EXPECTED_OPENCV_DISTRIBUTION,
        "opencv_runtime_version": EXPECTED_OPENCV_RUNTIME,
        "opencv5_verified": True,
    }


def _build(health: dict, source_sha: str) -> dict:
    return build_deployment_evidence(
        health,
        source_sha=source_sha,
        image_identifier="123456789012.dkr.ecr.us-east-1.amazonaws.com/hal-labsight@sha256:" + "b" * 64,
        service_url="example.us-east-1.awsapprunner.com",
        service_arn="arn:aws:apprunner:us-east-1:123456789012:service/hal-labsight/abc",
        region="us-east-1",
    )


def test_deployment_evidence_is_readiness_compatible_and_fail_closed():
    source_sha = "a" * 40
    record = _build(_health(source_sha), source_sha)

    assert record["source_git_sha"] == source_sha
    assert record["opencv"] == {
        "distribution_version": EXPECTED_OPENCV_DISTRIBUTION,
        "runtime_version": EXPECTED_OPENCV_RUNTIME,
        "verified": True,
    }
    assert record["aws"]["ecr_image_digest"] == "sha256:" + "b" * 64
    assert record["aws"]["app_runner_url"].startswith("https://")
    assert record["aws"]["health"]["source_sha"] == source_sha
    assert record["aws"]["cloudwatch_evidence"] is False
    assert record["responsible_use"]["diagnostic_claims"] is False


def test_deployment_evidence_rejects_source_sha_mismatch():
    source_sha = "a" * 40
    with pytest.raises(ValueError, match="source_sha mismatch"):
        _build(_health("c" * 40), source_sha)


def test_deployment_evidence_rejects_non_exact_opencv_runtime():
    source_sha = "a" * 40
    health = _health(source_sha)
    health["opencv_runtime_version"] = "5.1.0"
    with pytest.raises(ValueError, match="exact opencv-python"):
        _build(health, source_sha)


def test_deployment_evidence_rejects_mutable_or_invalid_image_identifier():
    source_sha = "a" * 40
    with pytest.raises(ValueError, match="immutable ECR"):
        build_deployment_evidence(
            _health(source_sha),
            source_sha=source_sha,
            image_identifier="123456789012.dkr.ecr.us-east-1.amazonaws.com/hal-labsight:latest",
            service_url="example.us-east-1.awsapprunner.com",
            service_arn="arn:aws:apprunner:us-east-1:123456789012:service/hal-labsight/abc",
            region="us-east-1",
        )
