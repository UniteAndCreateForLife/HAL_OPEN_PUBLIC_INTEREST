import hashlib
import json
from pathlib import Path

import cv2
import pytest

from labsight.corpus import evaluate_corpus, load_manifest
from labsight.synthetic import microscopy_scene


def _fixture(tmp_path: Path, *, digest_override: str | None = None):
    image = microscopy_scene(seed=31)
    image_path = tmp_path / "sample.png"
    assert cv2.imwrite(str(image_path), image)
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    manifest = {
        "purpose": "image_quality_control_only",
        "items": [{
            "id": "sample-001", "path": "sample.png", "sha256": digest_override or digest,
            "source_url": "https://example.org/open-microscopy/sample-001",
            "license": "CC-BY-4.0", "attribution": "Synthetic test fixture",
            "expected_qc_status": "accept",
        }],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_provenance_verified_corpus_is_scored(tmp_path):
    report = evaluate_corpus(_fixture(tmp_path), tmp_path)
    assert report["purpose"] == "image_quality_control_only"
    assert report["diagnostic_claims"] is False
    assert report["samples"] == 1
    assert report["qc_agreement"] == 1.0
    assert report["items"][0]["sha256"]
    assert len(report["manifest_sha256"]) == 64
    assert len(report["evaluation_id"]) == 64
    assert report["failure_analysis"]["failure_count"] == 0
    safety = report["failure_analysis"]["safety"]
    assert safety["unsafe_accept_count"] == 0
    assert safety["weighted_failure_points"] == 0
    assert safety["normalized_qc_risk"] == 0.0
    assert report["failure_analysis"]["per_expected_status"]["accept"]["recall"] == 1.0
    assert report["runtime"]["opencv"]
    assert isinstance(report["runtime"]["opencv5_verified"], bool)
    assert report["latency_ms"]["p95"] >= 0


def test_failure_analysis_records_mismatch_without_diagnostic_inference(tmp_path):
    path = _fixture(tmp_path)
    data = json.loads(path.read_text())
    data["items"][0]["expected_qc_status"] = "human_review"
    path.write_text(json.dumps(data))
    report = evaluate_corpus(path, tmp_path)
    analysis = report["failure_analysis"]
    assert report["diagnostic_claims"] is False
    assert report["qc_agreement"] == 0.0
    assert analysis["failure_count"] == 1
    assert analysis["failure_ids"] == ["sample-001"]
    assert analysis["confusion_matrix"]["human_review"]["accept"] == 1
    assert analysis["per_expected_status"]["human_review"]["recall"] == 0.0
    safety = analysis["safety"]
    assert safety["unsafe_accept_count"] == 1
    assert safety["unsafe_accept_ids"] == ["sample-001"]
    assert safety["false_rejection_count"] == 0
    assert safety["risk_weighting"] == {"unsafe_accept": 4, "false_rejection": 1}
    assert safety["weighted_failure_points"] == 4
    assert safety["normalized_qc_risk"] == 1.0


def test_false_rejection_is_separate_and_lower_weight_than_unsafe_accept(tmp_path):
    path = _fixture(tmp_path)
    data = json.loads(path.read_text())
    image = cv2.imread(str(tmp_path / "sample.png"))
    blurred = cv2.GaussianBlur(image, (0, 0), 12.0)
    assert cv2.imwrite(str(tmp_path / "sample.png"), blurred)
    data["items"][0]["sha256"] = hashlib.sha256((tmp_path / "sample.png").read_bytes()).hexdigest()
    path.write_text(json.dumps(data))
    report = evaluate_corpus(path, tmp_path)
    safety = report["failure_analysis"]["safety"]
    assert report["items"][0]["expected_qc_status"] == "accept"
    assert report["items"][0]["actual_qc_status"] != "accept"
    assert safety["unsafe_accept_count"] == 0
    assert safety["false_rejection_count"] == 1
    assert safety["false_rejection_ids"] == ["sample-001"]
    assert safety["weighted_failure_points"] == 1
    assert safety["normalized_qc_risk"] == 0.25


def test_hash_mismatch_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        evaluate_corpus(_fixture(tmp_path, digest_override="0" * 64), tmp_path)


def test_manifest_requires_qc_only_purpose(tmp_path):
    path = _fixture(tmp_path); data = json.loads(path.read_text()); data["purpose"] = "diagnosis"; path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="image_quality_control_only"): load_manifest(path)


def test_manifest_requires_license_and_attribution(tmp_path):
    path = _fixture(tmp_path); data = json.loads(path.read_text()); data["items"][0]["license"] = ""; path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="license and attribution"): load_manifest(path)


def test_manifest_rejects_invalid_expected_status(tmp_path):
    path = _fixture(tmp_path); data = json.loads(path.read_text()); data["items"][0]["expected_qc_status"] = "diagnose_cancer"; path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unsupported expected_qc_status"): load_manifest(path)


def test_manifest_rejects_non_hex_digest(tmp_path):
    path = _fixture(tmp_path); data = json.loads(path.read_text()); data["items"][0]["sha256"] = "z" * 64; path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="hexadecimal digest"): load_manifest(path)


def test_manifest_rejects_duplicate_ids(tmp_path):
    path = _fixture(tmp_path); data = json.loads(path.read_text()); data["items"].append(dict(data["items"][0])); path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="duplicate or empty corpus id"): load_manifest(path)


def test_evaluation_id_is_stable_across_manifest_formatting(tmp_path):
    path = _fixture(tmp_path); first = evaluate_corpus(path, tmp_path); data = json.loads(path.read_text()); path.write_text(json.dumps(data, indent=4, sort_keys=True)); second = evaluate_corpus(path, tmp_path)
    assert first["evaluation_id"] == second["evaluation_id"]
    assert first["manifest_sha256"] != second["manifest_sha256"]


def test_evaluation_id_changes_when_qc_expectation_changes(tmp_path):
    path = _fixture(tmp_path); first = evaluate_corpus(path, tmp_path); data = json.loads(path.read_text()); data["items"][0]["expected_qc_status"] = "human_review"; path.write_text(json.dumps(data)); second = evaluate_corpus(path, tmp_path)
    assert first["evaluation_id"] != second["evaluation_id"]


def test_agentic_first_action_and_enhancement_expectations_are_scored(tmp_path):
    image = microscopy_scene(seed=31, illumination_gradient=1.0)
    image_path = tmp_path / "sample.png"; assert cv2.imwrite(str(image_path), image)
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    manifest = {"purpose": "image_quality_control_only", "items": [{
        "id": "sample-agentic", "path": "sample.png", "sha256": digest,
        "source_url": "https://data.broadinstitute.org/bbbc/example.png",
        "source_page_url": "https://bbbc.broadinstitute.org/BBBC038", "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/", "attribution": "BBBC038v1 contributors",
        "derivation": "controlled_illumination_gradient", "expected_qc_status": "accept",
        "expected_first_action": "enhance_and_reanalyze", "expected_enhancement": True,
    }]}
    manifest_path = tmp_path / "manifest-agentic.json"; manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = evaluate_corpus(manifest_path, tmp_path)
    assert report["qc_agreement"] == 1.0
    assert report["first_action_agreement"] == 1.0
    assert report["enhancement_agreement"] == 1.0
    assert report["combined_expectation_agreement"] == 1.0
    assert report["items"][0]["actual_first_action"] == "enhance_and_reanalyze"
    assert report["failure_analysis"]["first_action"]["failure_count"] == 0


def test_agentic_action_mismatch_is_visible(tmp_path):
    path = _fixture(tmp_path); data = json.loads(path.read_text()); data["items"][0]["expected_qc_status"] = None; data["items"][0]["expected_first_action"] = "request_recapture_focus"; path.write_text(json.dumps(data))
    report = evaluate_corpus(path, tmp_path)
    assert report["first_action_agreement"] == 0.0
    assert report["combined_expectation_agreement"] == 0.0
    assert report["failure_analysis"]["first_action"]["failure_ids"] == ["sample-001"]


def test_extended_provenance_fields_are_validated(tmp_path):
    path = _fixture(tmp_path); data = json.loads(path.read_text()); item = data["items"][0]
    item["source_page_url"] = "https://bbbc.broadinstitute.org/BBBC038"; item["license_url"] = "https://creativecommons.org/publicdomain/zero/1.0/"; item["parent_sha256"] = "0" * 64; item["derivation"] = "native"; path.write_text(json.dumps(data))
    parsed = load_manifest(path)
    assert parsed[0].source_page_url.endswith("BBBC038")
    assert parsed[0].parent_sha256 == "0" * 64
