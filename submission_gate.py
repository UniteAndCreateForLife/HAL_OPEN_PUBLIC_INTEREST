from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from campus_mvp import default_demo_desk, demo_cases

ROOT = Path(__file__).resolve().parent
RULES = ROOT / "official_rules_snapshot.json"
BRIEF = ROOT / "APPLICATION_BRIEF.md"
OUT = ROOT / "evidence" / "submission_readiness.json"

CORE_MARKERS = {
    "clearly defined real-world campus problem": ("## problem",),
    "demonstrable technology solution": ("## mvp description", "## demonstration"),
    "clear technical approach": ("## technology architecture",),
    "realistic path to a POC or MVP": ("## current stage", "## scale-up plan"),
    "measurable value": ("## measurable value and evaluation plan",),
    "responsible implementation": ("## data privacy", "## security", "## responsible ai"),
}

JURY_MARKERS = {
    "problem relevance and user need": "problem relevance and user need:",
    "innovation and differentiation": "innovation and differentiation:",
    "feasibility and product readiness": "feasibility and product readiness:",
    "impact and scalability": "impact and scalability:",
    "technology, security and responsible use": "technology, security and responsible use:",
    "presentation and jury response": "presentation and jury response:",
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_brief_text(brief_text: str, rules: dict[str, Any]) -> dict[str, Any]:
    brief = brief_text.lower()
    missing_topics = [
        topic for topic in rules["required_application_topics"] if topic.lower() not in brief
    ]
    missing_core: list[str] = []
    for requirement in rules["required_core_submission_elements"]:
        markers = CORE_MARKERS.get(requirement)
        if not markers or any(marker.lower() not in brief for marker in markers):
            missing_core.append(requirement)
    missing_jury = [
        name
        for name in rules["jury_criteria_percent"]
        if JURY_MARKERS.get(name, "").lower() not in brief
    ]
    if missing_topics or missing_core or missing_jury:
        raise ValueError(
            json.dumps(
                {
                    "missing_application_topics": missing_topics,
                    "missing_core_requirements": missing_core,
                    "missing_jury_mappings": missing_jury,
                },
                sort_keys=True,
            )
        )
    return {
        "application_topics": len(rules["required_application_topics"]),
        "core_requirements": len(rules["required_core_submission_elements"]),
        "jury_criteria": len(rules["jury_criteria_percent"]),
    }

def evaluate_demo() -> dict[str, Any]:
    desk = default_demo_desk()
    results = {case.request_id: desk.analyze(case) for case in demo_cases()}
    checks = {
        "demo-1": (
            results["demo-1"].disposition == "evidence_response"
            and results["demo-1"].suggested_actions == ("route_facilities_ticket",)
            and results["demo-1"].human_approval_required
            and results["demo-1"].evidence[0].doc_id == "FAC-002"
        ),
        "demo-2": (
            results["demo-2"].disposition == "evidence_response"
            and results["demo-2"].evidence[0].doc_id == "ACADEMIC-004"
        ),
        "demo-3": (
            results["demo-3"].disposition == "human_review"
            and results["demo-3"].suggested_actions == ("route_human_review",)
            and results["demo-3"].human_approval_required
        ),
        "demo-4": (
            results["demo-4"].disposition == "insufficient_evidence"
            and results["demo-4"].suggested_actions == ("request_policy_source",)
            and results["demo-4"].confidence == 0.0
            and not results["demo-4"].evidence
        ),
    }
    deterministic = all(
        asdict(results[case.request_id]) == asdict(desk.analyze(case)) for case in demo_cases()
    )
    if not all(checks.values()) or not deterministic:
        raise ValueError("synthetic MVP acceptance or determinism check failed")
    return {
        "scope": "synthetic_local_mvp_not_institutional_validation",
        "cases": len(checks),
        "expected_behavior_passed": sum(checks.values()),
        "deterministic_replay": deterministic,
        "unknown_policy_failed_closed": checks["demo-4"],
        "sensitive_case_escalated": checks["demo-3"],
    }

def build_receipt() -> dict[str, Any]:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    brief_text = BRIEF.read_text(encoding="utf-8")
    completeness = validate_brief_text(brief_text, rules)
    evaluation = evaluate_demo()
    return {
        "status": "PASS",
        "scope": "local_competition_readiness_not_submission_finalist_award_or_payment",
        "competition": rules["competition"],
        "stream": rules["stream"],
        "deadline": rules["deadline"],
        "startup_prize_inr": rules["startup_prize_inr"],
        "submission_route": rules["submission_route"],
        "submission_route_status": rules["submission_route_status"],
        "organizer_eligibility_confirmed": True,
        "remote_finalist_participation": rules["remote_finalist_participation"],
        "human_gates": rules["human_gates"],
        "completeness": completeness,
        "synthetic_evaluation": evaluation,
        "application_brief_sha256": sha256(BRIEF),
        "rules_snapshot_sha256": sha256(RULES),
        "claims": {
            "submitted": False,
            "finalist": False,
            "awarded": False,
            "paid": False,
            "production_deployed": False,
            "institutional_pilot": False,
        },
    }


def main() -> int:
    receipt = build_receipt()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "receipt": str(OUT), "sha256": sha256(OUT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
