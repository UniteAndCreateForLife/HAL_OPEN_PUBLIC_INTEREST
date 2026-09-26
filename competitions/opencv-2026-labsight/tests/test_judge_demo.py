from fastapi.testclient import TestClient

from labsight.api import app
from labsight.judge_demo import JUDGE_SCENARIOS, RESPONSIBLE_USE, summarize_judge_suite


client = TestClient(app)


def test_judge_demo_endpoint_proves_expected_agentic_flow():
    response = client.get("/demo/judge", headers={"x-request-id": "judge-proof"})
    assert response.status_code == 200
    body = response.json()

    assert body["schema_version"] == "1.0"
    assert body["evidence_scope"] == "live_runtime_demo_not_aws_by_itself"
    assert body["all_expectations_met"] is True
    assert len(body["scenarios"]) == 4

    uneven = next(item for item in body["scenarios"] if item["name"] == "uneven")
    assert uneven["observed_first_action"] == "enhance_and_reanalyze"
    assert uneven["observed_final_action"] == "accept"
    assert uneven["used_enhancement"] is True
    assert len(uneven["trace"]) == 2
    assert body["agentic_vision"]["opencv_observation_changes_next_action"] is True
    assert body["agentic_vision"]["second_visual_pass"] is True

def test_judge_demo_preserves_responsible_use_and_runtime_provenance():
    body = client.get("/demo/judge").json()

    assert body["responsible_use"] == RESPONSIBLE_USE
    assert body["responsible_use"]["diagnostic_claims"] is False
    assert "diagnosis" in body["responsible_use"]["not_for"]
    assert body["runtime"]["service"] == "hal-labsight"
    assert body["runtime"]["source_sha"] == body["runtime"]["build_sha"]
    assert isinstance(body["runtime"]["opencv5_verified"], bool)


def test_judge_scenario_contract_is_complete_and_unique():
    names = [scenario.name for scenario in JUDGE_SCENARIOS]
    assert names == ["clean", "blurred", "uneven", "clipped"]
    assert len(set(names)) == len(names)
    assert all(s.expected_first_action for s in JUDGE_SCENARIOS)
    assert all(s.expected_final_action for s in JUDGE_SCENARIOS)


def test_judge_summary_fails_closed_when_agentic_trace_is_missing():
    results = {}
    for scenario in JUDGE_SCENARIOS:
        results[scenario.name] = {
            "status": scenario.expected_final_action,
            "used_enhancement": False,
            "trace": [],
        }
    summary = summarize_judge_suite(
        results,
        runtime={"opencv5_verified": False, "source_sha": "unknown"},
    )

    assert summary["all_expectations_met"] is False
    assert summary["agentic_vision"]["opencv_observation_changes_next_action"] is False
    assert summary["agentic_vision"]["second_visual_pass"] is False
