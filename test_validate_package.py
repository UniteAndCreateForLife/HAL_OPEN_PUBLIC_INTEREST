import tempfile
import unittest
from pathlib import Path

from validate_package import ROOT, repository_relative_path


class ValidatePackagePrivacyTests(unittest.TestCase):
    def test_repository_evidence_path_is_portable(self):
        self.assertEqual(
            repository_relative_path(ROOT / "evidence" / "demo_receipt.json"),
            "evidence/demo_receipt.json",
        )

    def test_repository_evidence_path_rejects_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "receipt.json"
            if ROOT in outside.parents:
                self.skipTest("temporary directory unexpectedly inside repository")
            with self.assertRaisesRegex(ValueError, "inside the repository"):
                repository_relative_path(outside)


if __name__ == "__main__":
    unittest.main()
