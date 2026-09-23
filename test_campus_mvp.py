import json
import unittest
from dataclasses import asdict

from campus_mvp import CampusRequest, default_demo_desk


class CampusEvidenceDeskTests(unittest.TestCase):
    def setUp(self):
        self.desk = default_demo_desk()

    def test_facilities_request_routes_with_evidence(self):
        result = self.desk.analyze(CampusRequest("r1", "The library elevator is broken."))
        self.assertEqual(result.disposition, "evidence_response")
        self.assertEqual(result.suggested_actions, ("route_facilities_ticket",))
        self.assertTrue(result.human_approval_required)
        self.assertEqual(result.evidence[0].doc_id, "FAC-002")

    def test_sensitive_request_fails_closed_to_human_review(self):
        result = self.desk.analyze(CampusRequest("r2", "A student reports a mental health concern."))
        self.assertEqual(result.disposition, "human_review")
        self.assertEqual(result.suggested_actions, ("route_human_review",))
        self.assertTrue(result.human_approval_required)

    def test_unknown_request_does_not_invent_policy(self):
        result = self.desk.analyze(CampusRequest("r3", "What is the parking fine for zone Q?"))
        self.assertEqual(result.disposition, "insufficient_evidence")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.suggested_actions, ("request_policy_source",))

    def test_academic_answer_cites_policy(self):
        result = self.desk.analyze(CampusRequest("r4", "How should academic policy questions be answered?"))
        self.assertEqual(result.disposition, "evidence_response")
        self.assertEqual(result.evidence[0].doc_id, "ACADEMIC-004")
        self.assertFalse(result.human_approval_required)

    def test_same_request_has_deterministic_audit_id(self):
        request = CampusRequest("r5", "The engineering building light is broken.")
        first = self.desk.analyze(request)
        second = self.desk.analyze(request)
        self.assertEqual(first.audit_id, second.audit_id)
        self.assertEqual(asdict(first), asdict(second))

    def test_result_serializes_without_custom_encoder(self):
        result = self.desk.analyze(CampusRequest("r6", "What does the privacy policy say?"))
        rendered = json.dumps(asdict(result), sort_keys=True)
        self.assertIn("DATA-003", rendered)


if __name__ == "__main__":
    unittest.main()
