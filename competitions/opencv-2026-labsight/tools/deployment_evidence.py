from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_OPENCV_DISTRIBUTION = "5.0.0.93"
EXPECTED_OPENCV_RUNTIME = "5.0.0"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def build_deployment_evidence(
    health: dict[str, Any],
    *,
    source_sha: str,
    image_identifier: str,
    service_url: str,
    service_arn: str,
    region: str,
) -> dict[str, Any]:
    """Validate deployed provenance and emit a readiness-compatible AWS fragment."""

    source_sha = source_sha.lower()
    if not _SHA40.fullmatch(source_sha):
        raise ValueError("source SHA must be a 40-character hexadecimal Git SHA")

    deployed_sha = str(health.get("source_sha", "")).lower()
    if deployed_sha != source_sha:
        raise ValueError(
            f"deployed /health source_sha mismatch: {deployed_sha!r} != {source_sha!r}"
        )

    distribution = str(health.get("opencv_distribution_version", ""))
    runtime = str(health.get("opencv_runtime_version", ""))
    if (
        distribution != EXPECTED_OPENCV_DISTRIBUTION
        or runtime != EXPECTED_OPENCV_RUNTIME
        or health.get("opencv5_verified") is not True
    ):
        raise ValueError(
            "deployed runtime must prove exact "
            f"opencv-python=={EXPECTED_OPENCV_DISTRIBUTION} and cv2=={EXPECTED_OPENCV_RUNTIME}"
        )

    _, separator, digest = image_identifier.rpartition("@")
    digest = digest.lower()
    if not separator or not _DIGEST.fullmatch(digest):
        raise ValueError("image identifier must be immutable ECR repository@sha256:digest")

    url = service_url if service_url.startswith("https://") else f"https://{service_url}"
    normalized_health = dict(health)
    normalized_health["source_sha"] = source_sha

    return {
        "scope": "aws_deployment_fragment",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_sha": source_sha,
        "opencv": {
            "distribution_version": distribution,
            "runtime_version": runtime,
            "verified": True,
        },
        "aws": {
            "region": region,
            "ecr_image_digest": digest,
            "image_identifier": image_identifier,
            "app_runner_url": url,
            "service_arn": service_arn,
            "health": normalized_health,
            "cloudwatch_evidence": False,
        },
        "responsible_use": {
            "microscopy_qc_only": True,
            "diagnostic_claims": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate App Runner /health and emit LabSight AWS evidence"
    )
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--image-identifier", required=True)
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--service-arn", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    health = json.load(sys.stdin)
    record = build_deployment_evidence(
        health,
        source_sha=args.source_sha,
        image_identifier=args.image_identifier,
        service_url=args.service_url,
        service_arn=args.service_arn,
        region=args.region,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
