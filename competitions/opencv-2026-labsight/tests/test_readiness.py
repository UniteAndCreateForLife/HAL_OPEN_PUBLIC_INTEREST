import json
from pathlib import Path

from labsight.readiness import EXPECTED_CV2, EXPECTED_OPENCV, REQUIRED_STATIC_PATHS, evaluate_submission_readiness, main


def _make_static_tree(root: Path) -> None:
    for relative in REQUIRED_STATIC_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")


def _complete_evidence(root: Path) -> dict:
    source_sha = "a" * 40
    report = root / "evaluation" / "real" / "report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("{}\n", encoding="utf-8")
    return {
        "source_git_sha": source_sha,
        "opencv": {"distribution_version": EXPECTED_OPENCV, "runtime_version": EXPECTED_CV2, "verified": True},
        "aws": {
            "ecr_image_digest": "sha256:" + "b" * 64,
            "app_runner_url": "https://example.awsapprunner.com",
            "health": {
                "source_sha": source_sha,
                "opencv_distribution_version": EXPECTED_OPENCV,
                "opencv_runtime_version": EXPECTED_CV2,
                "opencv5_verified": True,
            },
            "cloudwatch_evidence": True,
        },
        "corpus": {
            "manifest_frozen": True,
            "provenance_verified": True,
            "samples": 5,
            "evaluation_report": "evaluation/real/report.json",
        },
        "evaluation": {
            "failure_cases_documented": True,
            "agentic_trace_documented": True,
            "deployed_endpoint_verified": True,
            "deployed_source_sha": source_sha,
            "deployed_judge_suite_passed": True,
            "deployed_real_corpus_scored": 15,
            "deployed_unsafe_accepts": 0,
        },
        "demo": {
            "video_url": "https://example.test/labsight-demo",
            "video_duration_seconds": 299,
        },
        "responsible_use": {
            "microscopy_qc_only": True,
            "diagnostic_claims": False,
        },
    }


def test_static_gate_requires_all_repository_artifacts(tmp_path):
    _make_static_tree(tmp_path)
    report = evaluate_submission_readiness(tmp_path, static_only=True)
    assert report["ready"] is True
    assert report["failed_checks"] == []

    (tmp_path / "Dockerfile").unlink()
    report = evaluate_submission_readiness(tmp_path, static_only=True)
    assert report["ready"] is False
    assert report["failed_checks"] == ["static_artifacts"]


def test_final_gate_accepts_complete_exact_evidence(tmp_path):
    _make_static_tree(tmp_path)
    report = evaluate_submission_readiness(tmp_path, _complete_evidence(tmp_path))
    assert report["ready"] is True
    assert report["failed_checks"] == []
    assert report["diagnostic_claims"] is False


def test_local_or_wrong_opencv_runtime_cannot_satisfy_competition_gate(tmp_path):
    _make_static_tree(tmp_path)
    evidence = _complete_evidence(tmp_path)
    evidence["opencv"] = {"distribution_version": "4.13.0.92", "runtime_version": "4.13.0", "verified": True}
    evidence["aws"]["health"]["opencv_distribution_version"] = "4.13.0.92"
    report = evaluate_submission_readiness(tmp_path, evidence)
    assert "opencv5_runtime" in report["failed_checks"]
    assert "deployed_health_provenance" in report["failed_checks"]

    evidence = _complete_evidence(tmp_path)
    evidence["opencv"] = {"distribution_version": EXPECTED_OPENCV, "runtime_version": "5.1.0", "verified": True}
    report = evaluate_submission_readiness(tmp_path, evidence)
    assert "opencv5_runtime" in report["failed_checks"]


def test_deployed_health_must_match_source_sha(tmp_path):
    _make_static_tree(tmp_path)
    evidence = _complete_evidence(tmp_path)
    evidence["aws"]["health"]["source_sha"] = "c" * 40
    report = evaluate_submission_readiness(tmp_path, evidence)
    assert "deployed_health_provenance" in report["failed_checks"]


def test_cli_writes_machine_readable_report(tmp_path, capsys):
    _make_static_tree(tmp_path)
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(_complete_evidence(tmp_path)), encoding="utf-8")
    output = tmp_path / "readiness.json"

    assert main(["--root", str(tmp_path), "--evidence", str(evidence_path), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ready"] is True
    assert json.loads(capsys.readouterr().out)["expected_opencv"] == EXPECTED_OPENCV


def test_final_gate_requires_source_bound_deployed_evaluation(tmp_path):
    _make_static_tree(tmp_path)
    evidence = _complete_evidence(tmp_path)
    evidence["evaluation"]["deployed_endpoint_verified"] = False
    report = evaluate_submission_readiness(tmp_path, evidence)
    assert "deployed_evaluation" in report["failed_checks"]

    evidence = _complete_evidence(tmp_path)
    evidence["evaluation"]["deployed_source_sha"] = "c" * 40
    report = evaluate_submission_readiness(tmp_path, evidence)
    assert "deployed_evaluation" in report["failed_checks"]
