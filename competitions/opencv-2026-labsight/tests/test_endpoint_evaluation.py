import hashlib
import json

import pytest

from tools.endpoint_evaluation import enrich_deployment_evidence, evaluate_endpoint


SOURCE_SHA = "a" * 40


def _health(source_sha: str = SOURCE_SHA) -> dict:
    return {
        "status": "ok",
        "source_sha": source_sha,
        "opencv_distribution_version": "5.0.0.93",
        "opencv_runtime_version": "5.0.0",
        "opencv5_verified": True,
    }


def _judge() -> dict:
    return {
        "all_expectations_met": True,
        "agentic_vision": {"opencv_observation_changes_next_action": True},
        "responsible_use": {"diagnostic_claims": False},
    }


def _result(final_action: str, first_action: str, enhanced: bool = False) -> dict:
    return {
        "status": final_action,
        "used_enhancement": enhanced,
        "trace": [{"decision": first_action}],
    }


def _manifest(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    specs = [
        ("blur", b"blur", "request_recapture_focus", "request_recapture_focus", False),
        ("clipped", b"clip", "request_recapture_exposure", "request_recapture_exposure", False),
        ("uneven", b"uneven", None, "enhance_and_reanalyze", True),
        ("native", b"native", None, None, None),
    ]
    items = []
    for name, payload, expected_final, expected_first, expected_enhancement in specs:
        path = images / f"{name}.png"
        path.write_bytes(payload)
        items.append({
            "id": name,
            "path": f"images/{name}.png",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "derivation": name,
            "expected_qc_status": expected_final,
            "expected_first_action": expected_first,
            "expected_enhancement": expected_enhancement,
        })
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "purpose": "image_quality_control_only",
        "diagnostic_claims": False,
        "dataset": "fixture",
        "source_locks": [{"id": "source"}],
        "items": items,
    }), encoding="utf-8")
    return manifest


def _transport(*analysis_results):
    responses = iter([_health(), _judge(), *analysis_results])

    def fake(method, url, payload, timeout):
        assert method in {"GET", "POST"}
        assert url.startswith("https://example.awsapprunner.com/")
        body = next(responses)
        return body, {"x-labsight-request-id": "fixture", "server-timing": "labsight;dur=1.0"}, 5.0

    return fake


def test_endpoint_evaluation_proves_exact_runtime_agentic_and_real_corpus(tmp_path):
    manifest = _manifest(tmp_path)
    record = evaluate_endpoint(
        "example.awsapprunner.com",
        SOURCE_SHA,
        manifest,
        transport=_transport(
            _result("request_recapture_focus", "request_recapture_focus"),
            _result("request_recapture_exposure", "request_recapture_exposure"),
            _result("accept", "enhance_and_reanalyze", True),
            _result("accept", "accept"),
        ),
    )
    assert record["scores"]["final_action_accuracy"] == 1.0
    assert record["scores"]["first_action_accuracy"] == 1.0
    assert record["scores"]["enhancement_accuracy"] == 1.0
    assert record["scores"]["unsafe_accepts"] == 0
    assert record["readiness_fragment"]["evaluation"]["deployed_endpoint_verified"] is True
    assert record["responsible_use"]["diagnostic_claims"] is False
    assert record["corpus"]["scored_items"] == 3


def test_endpoint_evaluation_rejects_source_sha_mismatch(tmp_path):
    manifest = _manifest(tmp_path)
    responses = iter([_health("b" * 40)])

    def fake(method, url, payload, timeout):
        return next(responses), {}, 1.0

    with pytest.raises(ValueError, match="source_sha"):
        evaluate_endpoint("https://example.awsapprunner.com", SOURCE_SHA, manifest, transport=fake)


def test_endpoint_evaluation_rejects_wrong_opencv_runtime(tmp_path):
    manifest = _manifest(tmp_path)
    health = _health()
    health["opencv_distribution_version"] = "4.13.0.92"
    responses = iter([health])

    def fake(method, url, payload, timeout):
        return next(responses), {}, 1.0

    with pytest.raises(ValueError, match="exact OpenCV 5"):
        evaluate_endpoint("https://example.awsapprunner.com", SOURCE_SHA, manifest, transport=fake)


def test_endpoint_evaluation_rejects_manifest_hash_mismatch(tmp_path):
    manifest = _manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["items"][0]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        evaluate_endpoint(
            "https://example.awsapprunner.com",
            SOURCE_SHA,
            manifest,
            transport=_transport(),
        )


def test_endpoint_evaluation_fails_readiness_on_unsafe_accept(tmp_path):
    manifest = _manifest(tmp_path)
    record = evaluate_endpoint(
        "https://example.awsapprunner.com",
        SOURCE_SHA,
        manifest,
        transport=_transport(
            _result("accept", "accept"),
            _result("request_recapture_exposure", "request_recapture_exposure"),
            _result("accept", "enhance_and_reanalyze", True),
            _result("accept", "accept"),
        ),
    )
    assert record["scores"]["unsafe_accepts"] == 1
    assert record["scores"]["all_scored_expectations_met"] is False
    assert record["readiness_fragment"]["evaluation"]["deployed_endpoint_verified"] is False



def test_endpoint_evaluation_enriches_matching_deployment_evidence(tmp_path):
    manifest = _manifest(tmp_path)
    endpoint_record = evaluate_endpoint(
        "https://example.awsapprunner.com",
        SOURCE_SHA,
        manifest,
        transport=_transport(
            _result("request_recapture_focus", "request_recapture_focus"),
            _result("request_recapture_exposure", "request_recapture_exposure"),
            _result("accept", "enhance_and_reanalyze", True),
            _result("accept", "accept"),
        ),
    )
    deployment = {
        "source_git_sha": SOURCE_SHA,
        "aws": {"app_runner_url": "https://example.awsapprunner.com"},
        "evaluation": {"failure_cases_documented": True},
    }
    enriched = enrich_deployment_evidence(deployment, endpoint_record)
    assert enriched["evaluation"]["failure_cases_documented"] is True
    assert enriched["evaluation"]["deployed_endpoint_verified"] is True
    assert enriched["evaluation"]["deployed_endpoint_report"]["scores"]["unsafe_accepts"] == 0


def test_endpoint_evaluation_refuses_wrong_deployment_url(tmp_path):
    manifest = _manifest(tmp_path)
    endpoint_record = evaluate_endpoint(
        "https://example.awsapprunner.com",
        SOURCE_SHA,
        manifest,
        transport=_transport(
            _result("request_recapture_focus", "request_recapture_focus"),
            _result("request_recapture_exposure", "request_recapture_exposure"),
            _result("accept", "enhance_and_reanalyze", True),
            _result("accept", "accept"),
        ),
    )
    deployment = {
        "source_git_sha": SOURCE_SHA,
        "aws": {"app_runner_url": "https://other.awsapprunner.com"},
    }
    with pytest.raises(ValueError, match="URL does not match"):
        enrich_deployment_evidence(deployment, endpoint_record)
