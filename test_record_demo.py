import tempfile
import unittest
from pathlib import Path

from record_demo import artifact_relative_path, build_story, source_hashes


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

    def test_artifact_receipt_path_is_portable_and_confined(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "HAL_CAMPUS_EVIDENCE_DESK_DEMO.mp4"
            self.assertEqual(
                artifact_relative_path(video, root),
                "HAL_CAMPUS_EVIDENCE_DESK_DEMO.mp4",
            )
            with self.assertRaisesRegex(ValueError, "inside its output directory"):
                artifact_relative_path(root.parent / "outside.mp4", root)


if __name__ == "__main__":
    unittest.main()
