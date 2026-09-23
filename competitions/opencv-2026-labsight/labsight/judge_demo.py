from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DemoScenario:
    name: str
    label: str
    params: dict[str, Any]
    expected_first_action: str
    expected_final_action: str


JUDGE_SCENARIOS = (
    DemoScenario("clean", "Clean capture", {}, "accept", "accept"),
    DemoScenario(
        "blurred",
        "Severe blur",
        {"blur_sigma": 5.0},
        "request_recapture_focus",
        "request_recapture_focus",
    ),
    DemoScenario(
        "uneven",
        "Uneven illumination",
        {"illumination_gradient": 1.0},
        "enhance_and_reanalyze",
        "accept",
    ),
    DemoScenario(
        "clipped",
        "Clipped exposure",
        {"clip_highlights": True},
        "request_recapture_exposure",
        "request_recapture_exposure",
    ),
)


RESPONSIBLE_USE = {
    "scope": "microscopy image-quality control",
    "diagnostic_claims": False,
    "not_for": [
        "diagnosis",
        "prognosis",
        "treatment",
        "biological identification",
    ],
}


def summarize_judge_suite(
    results: dict[str, dict[str, Any]],
    *,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    """Create a deterministic judge-facing evidence summary from live analyses."""
    scenario_summaries: list[dict[str, Any]] = []
    for spec in JUDGE_SCENARIOS:
        result = results[spec.name]
        trace = result.get("trace", [])
        first_action = trace[0].get("decision") if trace else None
        final_action = result.get("status")
        passed = (
            first_action == spec.expected_first_action
            and final_action == spec.expected_final_action
        )
        scenario_summaries.append({
            "name": spec.name,
            "label": spec.label,
            "expected_first_action": spec.expected_first_action,
            "observed_first_action": first_action,
            "expected_final_action": spec.expected_final_action,
            "observed_final_action": final_action,
            "used_enhancement": bool(result.get("used_enhancement")),
            "trace": trace,
            "passed": passed,
        })

    uneven = results["uneven"]
    uneven_trace = uneven.get("trace", [])
    agentic_proof = (
        bool(uneven.get("used_enhancement"))
        and len(uneven_trace) == 2
        and uneven_trace[0].get("decision") == "enhance_and_reanalyze"
        and uneven_trace[1].get("decision") == uneven.get("status")
    )
    all_expectations_met = all(item["passed"] for item in scenario_summaries)

    return {
        "schema_version": "1.0",
        "evidence_scope": "live_runtime_demo_not_aws_by_itself",
        "responsible_use": RESPONSIBLE_USE,
        "runtime": runtime,
        "scenarios": scenario_summaries,
        "agentic_vision": {
            "proved_by_scenario": "uneven",
            "opencv_observation_changes_next_action": agentic_proof,
            "tool": "CLAHE",
            "second_visual_pass": len(uneven_trace) == 2,
            "final_action": uneven.get("status"),
        },
        "all_expectations_met": all_expectations_met,
    }
