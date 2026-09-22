import hashlib
import json
from pathlib import Path

import cv2
import pytest

from labsight.corpus import evaluate_corpus, load_manifest
from labsight.synthetic import microscopy_scene


def _fixture(tmp_path: Path, *, digest_override: str | None = None):
    image = microscopy_scene(seed=31)
    image_path = tmp_path / "sample.png"
    assert cv2.imwrite(str(image_path), image)
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    manifest = {
        "purpose": "image_quality_control_only",
        "items": [{
            "id": "sample-001",
            "path": "sample.png",
            "sha256": digest_override or digest,
            "source_url": "https://example.org/open-microscopy/sample-001",
            "license": "CC-BY-4.0",
            "attribution": "Synthetic test fixture",
            "expected_qc_status": "accept",
        }],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_provenance_verified_corpus_is_scored(tmp_path):
    report = evaluate_corpus(_fixture(tmp_path), tmp_path)
    assert report["purpose"] == "image_quality_control_only"
    assert report["diagnostic_claims"] is False
    assert report["samples"] == 1
    assert report["qc_agreement"] == 1.0
    assert report["items"][0]["sha256"]


def test_hash_mismatch_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        evaluate_corpus(_fixture(tmp_path, digest_override="0" * 64), tmp_path)


def test_manifest_requires_qc_only_purpose(tmp_path):
    path = _fixture(tmp_path)
    data = json.loads(path.read_text())
    data["purpose"] = "diagnosis"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="image_quality_control_only"):
        load_manifest(path)


def test_manifest_requires_license_and_attribution(tmp_path):
    path = _fixture(tmp_path)
    data = json.loads(path.read_text())
    data["items"][0]["license"] = ""
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="license and attribution"):
        load_manifest(path)
