from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from artifact_io import write_json_lf
from campus_mvp import default_demo_desk, demo_cases

ROOT = Path(__file__).resolve().parent
RULES = ROOT / "official_rules_snapshot.json"
BRIEF = ROOT / "APPLICATION_BRIEF.md"
OUT = ROOT / "evidence" / "demo_receipt.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_relative_path(path: Path) -> str:
    """Return a portable repository-relative path or fail closed."""

    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("evidence path must remain inside the repository") from exc


def main() -> int:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    brief = BRIEF.read_text(encoding="utf-8").lower()
    missing = [topic for topic in rules["required_application_topics"] if topic.lower() not in brief]
    if missing:
        raise SystemExit(f"missing application topics: {missing}")

    desk = default_demo_desk()
    results = [asdict(desk.analyze(case)) for case in demo_cases()]
    by_id = {item["request_id"]: item for item in results}
    assert by_id["demo-1"]["suggested_actions"] == ("route_facilities_ticket",)
    assert by_id["demo-1"]["human_approval_required"] is True
    assert by_id["demo-2"]["evidence"][0]["doc_id"] == "ACADEMIC-004"
    assert by_id["demo-3"]["disposition"] == "human_review"
    assert by_id["demo-4"]["disposition"] == "insufficient_evidence"

    receipt = {
        "scope": "synthetic_local_competition_mvp_not_submission_or_production_evidence",
        "competition": rules["competition"],
        "deadline": rules["deadline"],
        "startup_prize_inr": rules["startup_prize_inr"],
        "application_brief_sha256": sha256(BRIEF),
        "rules_snapshot_sha256": sha256(RULES),
        "mvp_source_sha256": sha256(ROOT / "campus_mvp.py"),
        "test_source_sha256": sha256(ROOT / "test_campus_mvp.py"),
        "demo_results": results,
        "claims": {
            "submitted": False,
            "awarded": False,
            "paid": False,
            "production_deployed": False,
            "real_student_data_used": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_json_lf(OUT, receipt)
    print(json.dumps({
        "status": "PASS",
        "receipt": repository_relative_path(OUT),
        "receipt_sha256": sha256(OUT),
        "demo_cases": len(results),
        "required_topics": len(rules["required_application_topics"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
