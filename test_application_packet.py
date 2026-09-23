import copy
import json
import unittest

from application_packet import (
    BRIEF,
    RULES,
    build_packet,
    extract_application_fields,
    human_gate_map,
    render_markdown,
    verify_packet,
)


class ApplicationPacketTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads(RULES.read_text(encoding="utf-8"))
        self.brief = BRIEF.read_text(encoding="utf-8")

    def test_extracts_every_required_application_topic(self):
        fields = extract_application_fields(self.brief, self.rules)
        self.assertEqual(list(fields), self.rules["required_application_topics"])
        self.assertEqual(len(fields), 15)
        self.assertTrue(all(value.strip() for value in fields.values()))

    def test_missing_required_section_fails_closed(self):
        damaged = self.brief.replace("## Pricing approach", "## Pricing notes")
        with self.assertRaisesRegex(ValueError, "pricing approach"):
            extract_application_fields(damaged, self.rules)

    def test_human_gates_are_explicit_and_not_auto_attested(self):
        gates = human_gate_map(self.rules)
        self.assertEqual(len(gates), 4)
        self.assertEqual(gates["final_form_submission"], "REQUIRES_HUMAN_ACTION")
        self.assertTrue(
            all(
                state in {"REQUIRES_HUMAN_ACTION", "REQUIRES_HUMAN_ATTESTATION"}
                for state in gates.values()
            )
        )

    def test_current_packet_verifies_and_preserves_false_claims(self):
        packet = build_packet()
        result = verify_packet(packet, expected_head=packet["source_commit"])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["field_count"], 15)
        self.assertEqual(result["human_gate_count"], 4)
        self.assertTrue(all(value is False for value in packet["claims"].values()))

    def test_source_drift_is_rejected(self):
        packet = build_packet()
        with self.assertRaisesRegex(ValueError, "source commit drift"):
            verify_packet(packet, expected_head="0" * 40)

    def test_positive_competition_claim_is_rejected(self):
        packet = build_packet()
        damaged = copy.deepcopy(packet)
        damaged["claims"]["submitted"] = True
        with self.assertRaisesRegex(ValueError, "unsupported competition-state claim"):
            verify_packet(damaged, expected_head=packet["source_commit"])

    def test_rendered_markdown_marks_packet_as_preparation_only(self):
        packet = build_packet()
        rendered = render_markdown(packet)
        self.assertIn("Preparation artifact only", rendered)
        self.assertIn("## Competition-status claims", rendered)
        self.assertIn("- submitted: `false`", rendered)
        self.assertNotIn("submitted: `true`", rendered)


if __name__ == "__main__":
    unittest.main()
