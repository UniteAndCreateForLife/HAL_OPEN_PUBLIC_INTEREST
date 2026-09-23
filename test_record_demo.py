import unittest

from record_demo import build_story, source_hashes


class RecordedDemoTests(unittest.TestCase):
    def test_story_is_bound_to_real_demo_results(self):
        results, slides = build_story()
        self.assertEqual(len(results), 4)
        self.assertEqual(len(slides), 6)
        by_id = {item["request_id"]: item for item in results}
        self.assertEqual(by_id["demo-1"]["evidence"][0]["doc_id"], "FAC-002")
        self.assertEqual(by_id["demo-2"]["evidence"][0]["doc_id"], "ACADEMIC-004")
        self.assertEqual(by_id["demo-3"]["disposition"], "human_review")
        self.assertEqual(by_id["demo-4"]["disposition"], "insufficient_evidence")

    def test_source_hash_set_covers_demo_contract(self):
        hashes = source_hashes()
        self.assertIn("campus_mvp.py", hashes)
        self.assertIn("record_demo.py", hashes)
        self.assertIn("APPLICATION_BRIEF.md", hashes)
        self.assertTrue(all(len(value) == 64 for value in hashes.values()))


if __name__ == "__main__":
    unittest.main()
