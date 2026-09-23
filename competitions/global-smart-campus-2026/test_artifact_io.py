import tempfile
import unittest
from pathlib import Path

from artifact_io import write_json_lf


class ArtifactIoTests(unittest.TestCase):
    def test_json_bytes_are_deterministic_lf_on_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            write_json_lf(output, {"z": 2, "a": 1})
            self.assertEqual(
                output.read_bytes(),
                b'{\n  "a": 1,\n  "z": 2\n}\n',
            )


if __name__ == "__main__":
    unittest.main()
