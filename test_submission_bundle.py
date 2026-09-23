from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import build_submission_bundle as bundle


class SubmissionBundleTests(unittest.TestCase):
    def make_inputs(self, root: Path) -> tuple[Path, Path]:
        (root / "evidence").mkdir(parents=True)
        rules = {"deadline": "2026-10-05", "startup_prize_inr": 50000}
        (root / "official_rules_snapshot.json").write_text(
            json.dumps(rules), encoding="utf-8"
        )
        video = root / "demo.mp4"
        video.write_bytes(b"video-bytes")
        video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
        demo = {
            "source_commit": "abc123",
            "video": str(video),
            "video_sha256": video_sha,
            "video_probe": {
                "duration_seconds": 49.0,
                "codec": "h264",
                "width": 1280,
                "height": 720,
            },
        }
        demo_path = root / "recorded-demo-receipt.json"
        demo_path.write_text(json.dumps(demo), encoding="utf-8")
        readiness = {
            "status": "PASS",
            "source_commit": "abc123",
            "deadline": "2026-10-05",
            "startup_prize_inr": 50000,
            "package_source_sha256": {},
            "recorded_demo": {
                "verified": True,
                "source_commit": "abc123",
                "video_sha256": video_sha,
            },
            "claims": {
                "submitted": False,
                "finalist": False,
                "awarded": False,
                "paid": False,
                "production_deployed": False,
                "institutional_pilot": False,
            },
        }
        readiness_path = root / "submission-readiness.json"
        readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
        return demo_path, readiness_path

    def test_validate_inputs_accepts_linked_current_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo, readiness = self.make_inputs(root)
            with patch.object(bundle, "git_head", return_value="abc123"):
                checked = bundle.validate_inputs(root, demo, readiness)
            self.assertEqual(checked["head"], "abc123")

    def test_validate_inputs_rejects_stale_demo_source_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo, readiness = self.make_inputs(root)
            with patch.object(bundle, "git_head", return_value="different"):
                with self.assertRaisesRegex(ValueError, "demo source commit drift"):
                    bundle.validate_inputs(root, demo, readiness)

    def test_validate_inputs_rejects_stale_readiness_source_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo, readiness = self.make_inputs(root)
            data = json.loads(readiness.read_text(encoding="utf-8"))
            data["source_commit"] = "old"
            readiness.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(bundle, "git_head", return_value="abc123"):
                with self.assertRaisesRegex(
                    ValueError, "readiness source commit drift"
                ):
                    bundle.validate_inputs(root, demo, readiness)

    def test_validate_inputs_rejects_unverified_demo_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo, readiness = self.make_inputs(root)
            data = json.loads(readiness.read_text(encoding="utf-8"))
            data["recorded_demo"]["verified"] = False
            readiness.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(bundle, "git_head", return_value="abc123"):
                with self.assertRaisesRegex(
                    ValueError, "does not verify the recorded demo"
                ):
                    bundle.validate_inputs(root, demo, readiness)

    def test_validate_inputs_rejects_tampered_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            demo, readiness = self.make_inputs(root)
            data = json.loads(demo.read_text(encoding="utf-8"))
            Path(data["video"]).write_bytes(b"tampered")
            with patch.object(bundle, "git_head", return_value="abc123"):
                with self.assertRaisesRegex(ValueError, "video SHA-256 mismatch"):
                    bundle.validate_inputs(root, demo, readiness)

    def test_safe_arcname_rejects_traversal_and_secret_paths(self) -> None:
        for name in (
            "../escape.txt",
            "/absolute.txt",
            "source/.env",
            "source/secrets/key.txt",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                bundle.safe_arcname(name)

    def test_verify_archive_detects_file_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bundle.zip"
            good = b"original"
            manifest = {
                "source_commit": "abc123",
                "claims": {
                    "submitted": False,
                    "finalist": False,
                    "awarded": False,
                    "paid": False,
                },
                "files": {"source/file.txt": hashlib.sha256(good).hexdigest()},
            }
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("MANIFEST.json", json.dumps(manifest))
                zf.writestr("source/file.txt", b"tampered")
            with self.assertRaisesRegex(ValueError, "archive SHA-256 mismatch"):
                bundle.verify_archive(archive)


if __name__ == "__main__":
    unittest.main()
