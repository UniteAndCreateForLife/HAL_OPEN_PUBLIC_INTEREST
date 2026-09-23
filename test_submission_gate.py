import json
import unittest

from submission_gate import (
    BRIEF,
    RULES,
    build_receipt,
    evaluate_demo,
    validate_brief_text,
    validate_demo_binding,
    validate_organizer_logistics,
)


class SubmissionGateTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads(RULES.read_text(encoding="utf-8"))
        self.brief = BRIEF.read_text(encoding="utf-8")

    def test_current_package_passes_completeness_gate(self):
        result = validate_brief_text(self.brief, self.rules)
        self.assertEqual(result["application_topics"], 15)
        self.assertEqual(result["core_requirements"], 6)
        self.assertEqual(result["jury_criteria"], 6)

    def test_missing_measurable_value_fails_closed(self):
        damaged = self.brief.replace("## Measurable value and evaluation plan", "## Evaluation notes")
        with self.assertRaisesRegex(ValueError, "measurable value"):
            validate_brief_text(damaged, self.rules)

    def test_missing_jury_mapping_fails_closed(self):
        damaged = self.brief.replace("- Presentation and jury response:", "- Presentation readiness:")
        with self.assertRaisesRegex(ValueError, "presentation and jury response"):
            validate_brief_text(damaged, self.rules)

    def test_synthetic_acceptance_package_is_deterministic(self):
        evaluation = evaluate_demo()
        self.assertEqual(evaluation["expected_behavior_passed"], 4)
        self.assertTrue(evaluation["deterministic_replay"])
        self.assertTrue(evaluation["unknown_policy_failed_closed"])
        self.assertTrue(evaluation["sensitive_case_escalated"])

    def test_receipt_preserves_human_and_claim_boundaries(self):
        receipt = build_receipt()
        self.assertTrue(receipt["organizer_eligibility_confirmed"])
        self.assertEqual(
            receipt["remote_finalist_participation"],
            "pre_recorded_presentation_and_mvp_demo_if_selected",
        )
        self.assertFalse(receipt["organizer_logistics"]["live_remote_required"])
        self.assertFalse(receipt["organizer_logistics"]["finalist_status_claimed"])
        self.assertFalse(receipt["recorded_demo"]["verified"])
        self.assertTrue(receipt["human_gates"])
        self.assertTrue(all(value is False for value in receipt["claims"].values()))
        self.assertEqual(sum(self.rules["jury_criteria_percent"].values()), 100)

    def test_missing_organizer_remote_route_fails_closed(self):
        damaged = dict(self.rules)
        damaged["remote_finalist_participation"] = "awaiting organizer response"
        with self.assertRaisesRegex(ValueError, "presentation route"):
            validate_organizer_logistics(damaged)

    def test_logistics_confirmation_does_not_claim_finalist_status(self):
        logistics = validate_organizer_logistics(self.rules)
        self.assertEqual(
            logistics["route"],
            "pre_recorded_presentation_and_mvp_demo_if_selected",
        )
        self.assertFalse(logistics["finalist_status_claimed"])

    def _demo_receipt(self):
        return {
            "source_commit": "abc123",
            "video_sha256": "a" * 64,
            "video_probe": {"duration_seconds": 49.0},
            "claims": {
                "submitted": False,
                "finalist": False,
                "awarded": False,
                "paid": False,
                "production_deployed": False,
                "real_student_data_used": False,
                "institutional_pilot": False,
            },
            "demo_results": [
                {"request_id": "demo-1", "disposition": "evidence_response"},
                {"request_id": "demo-2", "disposition": "evidence_response"},
                {"request_id": "demo-3", "disposition": "human_review"},
                {"request_id": "demo-4", "disposition": "insufficient_evidence"},
            ],
        }

    def test_demo_binding_accepts_exact_source_and_cases(self):
        result = validate_demo_binding(self._demo_receipt(), "abc123")
        self.assertTrue(result["verified"])
        self.assertEqual(result["demo_cases"], 4)

    def test_demo_binding_rejects_source_drift(self):
        with self.assertRaisesRegex(ValueError, "source commit drift"):
            validate_demo_binding(self._demo_receipt(), "different")

    def test_demo_binding_rejects_positive_claim(self):
        damaged = self._demo_receipt()
        damaged["claims"]["submitted"] = True
        with self.assertRaisesRegex(ValueError, "unsupported positive claim"):
            validate_demo_binding(damaged, "abc123")


if __name__ == "__main__":
    unittest.main()
