import pytest

from tools.container_probe import EXPECTED, validate_capture

SHA = "a" * 40


def capture():
    health = {
        "source_sha": SHA, "build_sha": SHA, "status": "ok",
        "opencv_distribution_version": "5.0.0.93",
        "opencv_runtime_version": "5.0.0", "opencv5_verified": True,
    }
    scenarios = {}
    for name, (status, enhancement) in EXPECTED.items():
        decisions = ["enhance_and_reanalyze", status] if enhancement else [status]
        scenarios[name] = {
            "status": status, "used_enhancement": enhancement,
            "trace": [{"decision": decision, "observation": {"focus_variance": 100}} for decision in decisions],
        }
    return health, scenarios


def test_complete_capture_remains_local_qc_evidence():
    report = validate_capture(SHA, *capture())
    assert report["passed"] is True
    assert report["diagnostic_claims"] is False
    assert report["aws_deployed"] is False
    assert report["purpose"] == "image_quality_control_only"
    assert "NOT AWS" in report["scope"]


@pytest.mark.parametrize("key,value", [
    ("source_sha", "b" * 40), ("build_sha", "b" * 40),
    ("opencv_distribution_version", "4.13.0.92"),
    ("opencv_distribution_version", "5.0.0.92"),
    ("opencv_runtime_version", "4.13.0"),
    ("opencv_runtime_version", "5.1.0"),
    ("opencv5_verified", "true"), ("opencv5_verified", False),
    ("status", "error"),
])
def test_wrong_source_or_runtime_is_rejected(key, value):
    health, scenarios = capture()
    health[key] = value
    with pytest.raises(ValueError):
        validate_capture(SHA, health, scenarios)


@pytest.mark.parametrize("sha", ["unknown", "a" * 12, "z" * 40])
def test_unverifiable_source_is_rejected(sha):
    with pytest.raises(ValueError, match="full lowercase Git SHA"):
        validate_capture(sha, *capture())

def test_missing_scenario_is_rejected():
    health, scenarios = capture()
    del scenarios["blurred"]
    with pytest.raises(ValueError, match="all four"):
        validate_capture(SHA, health, scenarios)


@pytest.mark.parametrize("key,value", [
    ("status", "human_review"), ("used_enhancement", False),
    ("trace", []),
    ("trace", [{"decision": "accept", "observation": {"focus_variance": 100}}]),
    ("trace", [{"decision": "enhance_and_reanalyze", "observation": {}},
               {"decision": "accept", "observation": {}}]),
])
def test_agentic_control_flow_failure_is_rejected(key, value):
    health, scenarios = capture()
    scenarios["uneven"][key] = value
    with pytest.raises(ValueError):
        validate_capture(SHA, health, scenarios)
