from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

EXPECTED_OPENCV = "5.0.0.93"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_STATIC_PATHS = (
    "Dockerfile",
    "requirements-competition.txt",
    "README.md",
    "docs/TECHNICAL_REPORT.md",
    "docs/ARCHITECTURE.md",
    "docs/AWS_ARCHITECTURE.md",
    "docs/VALIDATION.md",
    "aws/apprunner.yml",
)


def _check(checks: list[dict[str, Any]], check_id: str, ok: bool, detail: str) -> None:
    checks.append({"id": check_id, "ok": bool(ok), "detail": detail})


def evaluate_submission_readiness(
    project_root: str | Path,
    evidence: dict[str, Any] | None = None,
    *,
    static_only: bool = False,
) -> dict[str, Any]:
    """Evaluate competition submission readiness without inventing missing evidence.

    This gate is intentionally strict. Local OpenCV 4.x development results cannot
    satisfy the competition-runtime checks, and cloud/runtime claims must be backed
    by an explicit evidence document.
    """

    root = Path(project_root)
    evidence = evidence or {}
    checks: list[dict[str, Any]] = []

    missing = [path for path in REQUIRED_STATIC_PATHS if not (root / path).is_file()]
    _check(
        checks,
        "static_artifacts",
        not missing,
        "all required repository artifacts present" if not missing else f"missing: {', '.join(missing)}",
    )

    if not static_only:
        source_sha = str(evidence.get("source_git_sha", "")).lower()
        opencv = evidence.get("opencv") or {}
        aws = evidence.get("aws") or {}
        health = aws.get("health") or {}
        corpus = evidence.get("corpus") or {}
        evaluation = evidence.get("evaluation") or {}
        demo = evidence.get("demo") or {}
        responsible = evidence.get("responsible_use") or {}

        runtime_ok = opencv.get("version") == EXPECTED_OPENCV and opencv.get("verified") is True
        _check(
            checks,
            "opencv5_runtime",
            runtime_ok,
            f"requires executed cv2.__version__ == {EXPECTED_OPENCV}; recorded={opencv.get('version')!r}",
        )

        source_ok = bool(_SHA40.fullmatch(source_sha))
        _check(checks, "source_git_sha", source_ok, "40-character source Git SHA required")

        digest = str(aws.get("ecr_image_digest", "")).lower()
        _check(checks, "immutable_ecr_digest", bool(_DIGEST.fullmatch(digest)), "immutable sha256 ECR digest required")

        endpoint = str(aws.get("app_runner_url", ""))
        _check(checks, "app_runner_endpoint", endpoint.startswith("https://"), "HTTPS App Runner endpoint required")

        health_ok = (
            source_ok
            and str(health.get("source_sha", "")).lower() == source_sha
            and health.get("opencv_version") == EXPECTED_OPENCV
            and health.get("opencv5_verified") is True
        )
        _check(
            checks,
            "deployed_health_provenance",
            health_ok,
            "deployed /health must match source SHA and exact OpenCV competition runtime",
        )

        _check(
            checks,
            "aws_observability",
            aws.get("cloudwatch_evidence") is True,
            "CloudWatch/App Runner observability evidence required",
        )

        report_path = root / str(corpus.get("evaluation_report", ""))
        corpus_ok = (
            corpus.get("manifest_frozen") is True
            and corpus.get("provenance_verified") is True
            and isinstance(corpus.get("samples"), int)
            and corpus.get("samples", 0) > 0
            and bool(corpus.get("evaluation_report"))
            and report_path.is_file()
        )
        _check(
            checks,
            "real_corpus_evidence",
            corpus_ok,
            "frozen, provenance-verified non-empty microscopy corpus and evaluation report required",
        )

        evaluation_ok = (
            evaluation.get("failure_cases_documented") is True
            and evaluation.get("agentic_trace_documented") is True
        )
        _check(
            checks,
            "evaluation_and_agentic_trace",
            evaluation_ok,
            "failure analysis and perception-decision-action trace evidence required",
        )

        endpoint_or_live = endpoint.startswith("https://") or demo.get("live_demo_arranged") is True
        _check(
            checks,
            "judge_demo_access",
            endpoint_or_live,
            "working web endpoint or arranged live demonstration required",
        )

        duration = demo.get("video_duration_seconds")
        video_ok = (
            str(demo.get("video_url", "")).startswith("https://")
            and isinstance(duration, (int, float))
            and 0 < duration <= 300
        )
        _check(checks, "demo_video", video_ok, "judge-accessible video URL with duration <= 300 seconds required")

        responsible_ok = (
            responsible.get("microscopy_qc_only") is True
            and responsible.get("diagnostic_claims") is False
        )
        _check(
            checks,
            "responsible_use_boundary",
            responsible_ok,
            "must explicitly attest microscopy QC only and diagnostic_claims=false",
        )

    failed = [item["id"] for item in checks if not item["ok"]]
    return {
        "scope": "static" if static_only else "final_submission",
        "ready": not failed,
        "failed_checks": failed,
        "checks": checks,
        "expected_opencv": EXPECTED_OPENCV,
        "diagnostic_claims": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HAL LabSight competition submission-readiness gate")
    parser.add_argument("--root", default=".", help="LabSight project root")
    parser.add_argument("--evidence", help="JSON evidence document for final-submission checks")
    parser.add_argument("--static-only", action="store_true", help="check repository artifacts only")
    parser.add_argument("--output", help="optional path for the JSON readiness report")
    args = parser.parse_args(argv)

    if not args.static_only and not args.evidence:
        parser.error("--evidence is required unless --static-only is used")

    evidence: dict[str, Any] | None = None
    if args.evidence:
        evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))

    report = evaluate_submission_readiness(args.root, evidence, static_only=args.static_only)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
