import hashlib
import json
from pathlib import Path
import warnings
import zipfile

import cv2
import numpy as np
import pytest

from labsight.corpus import load_manifest
from tools import bbbc038_holdout as h


def png(image, compression=3):
    ok, encoded = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, compression])
    assert ok
    return encoded.tobytes()


def fixture(tmp_path):
    root = tmp_path / "development"
    root.mkdir()
    a = np.random.default_rng(7).integers(50, 190, (40, 40), dtype=np.uint8)
    b = np.random.default_rng(9).integers(50, 190, (40, 40), dtype=np.uint8)
    payload = png(a, 0)
    (root / "native.png").write_bytes(payload)
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"purpose": h.PURPOSE, "diagnostic_claims": False, "items": [{
        "id": "dev-native", "path": "native.png", "sha256": h.digest(payload),
        "source_url": h.SOURCE_PAGE, "license": "CC0-1.0", "attribution": "Synthetic unit fixture",
        "parent_sha256": h.digest(payload), "derivation": "native"}]}))
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for key, image in (("0", a), ("1", b), ("2", b)):
            image_id = key * 64
            z.writestr(f"{image_id}/images/{image_id}.png", png(image, 9))
    lock = h.freeze(archive, manifest, root)
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock, indent=2))
    return archive, manifest, root, lock_path, lock


def test_selection_is_deterministic_without_policy_evaluation(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "evaluate_corpus", lambda *a: pytest.fail("freeze must not score policy"))
    archive, manifest, root, _, lock = fixture(tmp_path)
    assert lock == h.freeze(archive, manifest, root)
    assert lock["candidate_sources"] == 3
    assert len(lock["sources"]) == 1
    assert len(lock["rejected"]) == 2
    assert lock["sources"][0]["id"] == "1" * 64
    assert lock["diagnostic_claims"] is False


def test_decoded_pixel_overlap_catches_reencoded_sources(tmp_path):
    _, _, _, _, lock = fixture(tmp_path)
    dev = lock["excluded_development"]
    first = lock["rejected"][0]
    assert first["sha256"] not in dev["raw_sha256"]
    assert first["pixel_sha256"] in dev["pixel_sha256"]


def test_build_seals_ancestry_and_keeps_native_unscored(tmp_path):
    archive, _, _, lock_path, lock = fixture(tmp_path)
    output = tmp_path / "built"
    manifest = h.build(archive, lock_path, output)
    assert manifest["source_count"] == 1
    assert len(load_manifest(output / "manifest.json")) == 4
    assert manifest["selection_lock_hash_scheme"] == h.TEXT_HASH_SCHEME
    assert manifest["selection_lock_sha256"] == h.text_digest(lock_path)
    native = next(i for i in manifest["items"] if i["derivation"] == "native")
    assert native["expected_qc_status"] is None
    assert native["expected_first_action"] is None
    assert native["expected_enhancement"] is None
    assert {i["parent_sha256"] for i in manifest["items"]} == {lock["sources"][0]["sha256"]}
    second = h.build(archive, lock_path, tmp_path / "second")
    assert manifest == second


def test_build_refuses_existing_output(tmp_path):
    archive, _, _, lock_path, _ = fixture(tmp_path)
    output = tmp_path / "built"
    h.build(archive, lock_path, output)
    original = (output / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        h.build(archive, lock_path, output)
    assert original == (output / "manifest.json").read_bytes()


def test_archive_hash_drift_rejected_before_output(tmp_path):
    archive, _, _, lock_path, _ = fixture(tmp_path)
    with archive.open("ab") as handle:
        handle.write(b"drift")
    with pytest.raises(ValueError, match="archive SHA256"):
        h.build(archive, lock_path, tmp_path / "built")
    assert not (tmp_path / "built").exists()


@pytest.mark.parametrize("field,value,match", [
    ("purpose", "diagnosis", "QC-only"),
    ("diagnostic_claims", True, "QC-only"),
    ("license", "unknown", "provenance"),
    ("sources", [], "selection lock"),
    ("policy_sha256", {}, "frozen policy"),
    ("stressors", [], "frozen policy"),
])
def test_mutated_lock_rejected(tmp_path, field, value, match):
    archive, _, _, lock_path, lock = fixture(tmp_path)
    lock[field] = value
    lock_path.write_text(json.dumps(lock))
    with pytest.raises(ValueError, match=match):
        h.build(archive, lock_path, tmp_path / "built")


def test_tampered_development_image_rejected(tmp_path):
    archive, manifest, root, _, _ = fixture(tmp_path)
    (root / "native.png").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="development image SHA256"):
        h.freeze(archive, manifest, root)


def test_missing_development_ancestry_rejected(tmp_path):
    archive, manifest, root, _, _ = fixture(tmp_path)
    data = json.loads(manifest.read_text())
    del data["items"][0]["parent_sha256"]
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="parent provenance"):
        h.freeze(archive, manifest, root)


@pytest.mark.parametrize("name", ["../escape.png", "/absolute.png", "a\\escape.png", "unexpected.png"])
def test_unsafe_or_unexpected_zip_paths_rejected(tmp_path, name):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(name, b"not an image")
    with pytest.raises(ValueError, match="ZIP member"):
        h.read_archive(archive)


def test_duplicate_zip_member_rejected(tmp_path):
    archive = tmp_path / "duplicates.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("x/", b"")
            z.writestr("x/", b"")
    with pytest.raises(ValueError, match="duplicate ZIP"):
        h.read_archive(archive)


def test_empty_and_fully_overlapping_sources_rejected(tmp_path):
    archive = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive, "w"):
        pass
    with pytest.raises(ValueError, match="no microscopy"):
        h.read_archive(archive)
    source = {"id": "x", "member": "x", "sha256": "a", "pixel_sha256": "b"}
    with pytest.raises(ValueError, match="no source-disjoint"):
        h.select_sources([source], {"raw_sha256": ["a"], "pixel_sha256": []})


def test_png_size_and_uint16_rejected():
    payload = bytearray(png(np.zeros((4, 4), dtype=np.uint8)))
    payload[16:20] = (100_000).to_bytes(4, "big")
    with pytest.raises(ValueError, match="dimensions"):
        h.decode_png(bytes(payload))
    with pytest.raises(ValueError, match="uint8"):
        h.decode_png(png(np.ones((4, 4), dtype=np.uint16)))


def test_evaluation_requires_executing_source_and_exact_runtime(tmp_path, monkeypatch):
    sha = "a" * 40
    monkeypatch.setenv("LABSIGHT_BUILD_SHA", "b" * 40)
    with pytest.raises(ValueError, match="source SHA"):
        h.evaluate(tmp_path / "missing", tmp_path, sha)
    monkeypatch.setenv("LABSIGHT_BUILD_SHA", sha)
    monkeypatch.setattr(h, "competition_runtime_info", lambda: {"opencv5_verified": False})
    with pytest.raises(ValueError, match="exact OpenCV 5"):
        h.evaluate(tmp_path / "missing", tmp_path, sha)


def test_evaluation_checks_frozen_policy_and_marks_non_aws(tmp_path, monkeypatch):
    archive, _, _, lock_path, _ = fixture(tmp_path)
    root = tmp_path / "built"
    h.build(archive, lock_path, root)
    manifest = root / "manifest.json"
    sha = "a" * 40
    monkeypatch.setenv("LABSIGHT_BUILD_SHA", sha)
    monkeypatch.setattr(h, "competition_runtime_info", lambda: {"opencv5_verified": True})
    monkeypatch.setattr(h, "evaluate_corpus", lambda *a: {"samples": 4, "diagnostic_claims": False})
    report = h.evaluate(manifest, root, sha)
    assert report["evidence_scope"] == "local_container_challenge_not_aws"
    assert report["source_count"] == 1
    assert report["diagnostic_claims"] is False
    monkeypatch.setattr(h, "policy_hashes", lambda: {})
    with pytest.raises(ValueError, match="frozen policy"):
        h.evaluate(manifest, root, sha)


def test_policy_lock_is_cross_platform_but_detects_content_change(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "PROJECT_ROOT", tmp_path)
    for name in h.POLICY_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# policy\nthreshold = 42\n")
    linux = h.policy_hashes()
    for name in h.POLICY_FILES:
        (tmp_path / name).write_bytes(b"# policy\r\nthreshold = 42\r\n")
    assert h.policy_hashes() == linux
    (tmp_path / h.POLICY_FILES[0]).write_bytes(b"# policy\nthreshold = 43\n")
    assert h.policy_hashes() != linux


def test_selection_lock_hash_is_cross_platform(tmp_path: Path):
    lock_path = tmp_path / "lock.json"
    lock_path.write_bytes(b'{"schema": 1}\n')
    linux = h.text_digest(lock_path)
    assert linux == hashlib.sha256(b'{"schema": 1}\n').hexdigest()
    lock_path.write_bytes(b'{"schema": 1}\r\n')
    assert h.text_digest(lock_path) == linux
    lock_path.write_bytes(b'{"schema": 2}\n')
    assert h.text_digest(lock_path) != linux
