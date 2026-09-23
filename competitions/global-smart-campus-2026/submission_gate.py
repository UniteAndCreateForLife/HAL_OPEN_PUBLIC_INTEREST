from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from artifact_io import write_json_lf
from campus_mvp import default_demo_desk, demo_cases
from record_demo import verify_receipt as verify_recorded_demo_receipt

ROOT = Path(__file__).resolve().parent
RULES = ROOT / "official_rules_snapshot.json"
BRIEF = ROOT / "APPLICATION_BRIEF.md"
OUT = ROOT / "evidence" / "submission_readiness.json"
PACKAGE_SOURCE_FILES = (
    "artifact_io.py",
    "campus_mvp.py",
    "record_demo.py",
    "submission_gate.py",
    "validate_package.py",
    "APPLICATION_BRIEF.md",
    "official_rules_snapshot.json",
)

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


def git_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def package_source_hashes() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in PACKAGE_SOURCE_FILES}


def validate_demo_binding(receipt: dict[str, Any], expected_source_commit: str) -> dict[str, Any]:
    if receipt.get("source_commit") != expected_source_commit:
        raise ValueError("recorded demo source commit drift")
    claims = receipt.get("claims")
    if not isinstance(claims, dict) or any(claims.values()):
        raise ValueError("recorded demo contains unsupported positive claim")
    video_sha = receipt.get("video_sha256", "")
    if len(video_sha) != 64 or any(ch not in "0123456789abcdef" for ch in video_sha.lower()):
        raise ValueError("recorded demo video SHA-256 is invalid")
    expected_dispositions = {
        "demo-1": "evidence_response",
        "demo-2": "evidence_response",
        "demo-3": "human_review",
        "demo-4": "insufficient_evidence",
    }
    results = receipt.get("demo_results") or []
    by_id = {item.get("request_id"): item for item in results if isinstance(item, dict)}
    observed = {
        key: by_id.get(key, {}).get("disposition") for key in expected_dispositions
    }
    if observed != expected_dispositions:
        raise ValueError("recorded demo acceptance cases are incomplete or changed")
    probe = receipt.get("video_probe") or {}
    duration = float(probe.get("duration_seconds", 0.0))
    if duration <= 0:
        raise ValueError("recorded demo duration is invalid")
    return {
        "verified": True,
        "source_commit": expected_source_commit,
        "video_sha256": video_sha,
        "duration_seconds": duration,
        "demo_cases": len(expected_dispositions),
    }


def validate_recorded_demo(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise ValueError("ffprobe is required to verify the recorded demo")
    receipt = verify_recorded_demo_receipt(path, ffprobe)
    return validate_demo_binding(receipt, git_head())


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


def validate_organizer_logistics(rules: dict[str, Any]) -> dict[str, Any]:
    expected = "pre_recorded_presentation_and_mvp_demo_if_selected"
    if rules.get("remote_finalist_participation") != expected:
        raise ValueError("organizer-confirmed finalist presentation route missing or changed")
    if not rules.get("organizer_email_logistics"):
        raise ValueError("organizer logistics confirmation is missing")
    if not rules.get("organizer_email_logistics_received_at_utc"):
        raise ValueError("organizer logistics timestamp is missing")
    return {
        "route": expected,
        "confirmation_received_at_utc": rules["organizer_email_logistics_received_at_utc"],
        "live_remote_required": False,
        "finalist_status_claimed": False,
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


def build_receipt(demo_receipt: Path | None = None) -> dict[str, Any]:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    brief_text = BRIEF.read_text(encoding="utf-8")
    completeness = validate_brief_text(brief_text, rules)
    logistics = validate_organizer_logistics(rules)
    evaluation = evaluate_demo()
    source_commit = git_head()
    recorded_demo = (
        validate_recorded_demo(demo_receipt)
        if demo_receipt is not None
        else {"verified": False, "reason": "no recorded-demo receipt supplied"}
    )
    return {
        "status": "PASS",
        "scope": "local_competition_readiness_not_submission_finalist_award_or_payment",
        "source_commit": source_commit,
        "package_source_sha256": package_source_hashes(),
        "recorded_demo": recorded_demo,
        "competition": rules["competition"],
        "stream": rules["stream"],
        "deadline": rules["deadline"],
        "startup_prize_inr": rules["startup_prize_inr"],
        "submission_route": rules["submission_route"],
        "submission_route_status": rules["submission_route_status"],
        "organizer_eligibility_confirmed": True,
        "remote_finalist_participation": rules["remote_finalist_participation"],
        "organizer_logistics": logistics,
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
    parser = argparse.ArgumentParser(
        description="Validate the Global Smart Campus application package"
    )
    parser.add_argument("--demo-receipt", type=Path)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    receipt = build_receipt(args.demo_receipt)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json_lf(output, receipt)
    print(
        json.dumps(
            {
                "status": "PASS",
                "receipt": str(output),
                "sha256": sha256(output),
                "source_commit": receipt["source_commit"],
                "recorded_demo_verified": receipt["recorded_demo"]["verified"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
