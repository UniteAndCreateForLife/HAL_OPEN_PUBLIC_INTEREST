"""Deterministic contracts for the judge-demo recording evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.judge_video_capture import (
    Caption,
    EXPECTED_ACTIONS,
    REQUIRED_PRESENTATION_COVERAGE,
    _vtt_time,
    build_presentation_evidence,
    load_holdout_receipt,
    sha256_file,
    validate_analysis,
    validate_health,
    write_captions,
    write_manifest,
)


def exact_health() -> dict:
    return {
        "source_sha": "a" * 40,
        "build_sha": "a" * 40,
        "opencv_distribution_version": "5.0.0.93",
        "opencv_runtime_version": "5.0.0",
        "opencv5_verified": True,
    }


def analysis(name: str) -> dict:
    first, final = EXPECTED_ACTIONS[name]
    trace = [{"decision": first}]
    if name == "uneven":
        trace.append({"decision": final})
    return {"status": final, "trace": trace, "used_enhancement": name == "uneven"}


def holdout() -> dict:
    return {
        "source_sha": "b" * 40,
        "samples": 260,
        "scored_samples": 130,
        "qc_agreement": 0.8769230769,
        "final_failure_count": 16,
        "unsafe_accept_count": 0,
        "limitations": ["controlled expectations"],
        "diagnostic_claims": False,
    }


def test_exact_health_is_accepted():
    validate_health(exact_health(), "a" * 40)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_sha", "b" * 40),
        ("build_sha", "b" * 40),
        ("opencv_distribution_version", "4.13.0.92"),
        ("opencv_runtime_version", "4.13.0"),
        ("opencv5_verified", False),
    ],
)
def test_health_fails_closed(field, value):
    payload = exact_health()
    payload[field] = value
    with pytest.raises(ValueError):
        validate_health(payload, "a" * 40)


@pytest.mark.parametrize("name", sorted(EXPECTED_ACTIONS))
def test_live_scenario_contract(name):
    observed = validate_analysis(name, analysis(name))
    assert observed["passed"] is True
    assert observed["observed_final_action"] == EXPECTED_ACTIONS[name][1]


@pytest.mark.parametrize("name", sorted(EXPECTED_ACTIONS))
def test_wrong_final_action_is_rejected(name):
    payload = analysis(name)
    payload["status"] = (
        "accept" if payload["status"] != "accept" else "request_recapture_focus"
    )
    with pytest.raises(ValueError, match="expected"):
        validate_analysis(name, payload)


def test_empty_trace_is_rejected():
    payload = analysis("clean")
    payload["trace"] = []
    with pytest.raises(ValueError, match="missing"):
        validate_analysis("clean", payload)


def test_uneven_requires_second_pass():
    payload = analysis("uneven")
    payload["trace"] = payload["trace"][:1]
    with pytest.raises(ValueError, match="second visual pass"):
        validate_analysis("uneven", payload)


def test_uneven_requires_enhancement_flag():
    payload = analysis("uneven")
    payload["used_enhancement"] = False
    with pytest.raises(ValueError, match="CLAHE"):
        validate_analysis("uneven", payload)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00:00.000"),
        (1.2345, "00:00:01.234"),
        (61.001, "00:01:01.001"),
        (3661.9, "01:01:01.900"),
    ],
)
def test_vtt_time(seconds, expected):
    assert _vtt_time(seconds) == expected


def test_vtt_writer_preserves_disclosures(tmp_path):
    target = tmp_path / "demo.vtt"
    write_captions(target, [Caption(0, 2, "Scope", "Not diagnosis; not AWS evidence.")])
    text = target.read_text(encoding="utf-8")
    assert text.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:02.000" in text
    assert "Not diagnosis; not AWS evidence." in text


def test_vtt_writer_clamps_last_caption_to_video_duration(tmp_path):
    target = tmp_path / "demo.vtt"
    write_captions(target, [Caption(1, 7, "End", "Still bounded")], max_duration=5.0)
    assert "00:00:01.000 --> 00:00:05.000" in target.read_text(encoding="utf-8")


def test_vtt_writer_rejects_caption_start_after_video(tmp_path):
    with pytest.raises(ValueError, match="after"):
        write_captions(
            tmp_path / "demo.vtt",
            [Caption(6, 7, "Late", "Invalid")],
            max_duration=5.0,
        )


def test_holdout_receipt_is_loaded(tmp_path):
    target = tmp_path / "holdout.json"
    target.write_text(json.dumps(holdout()), encoding="utf-8")
    assert load_holdout_receipt(target)["unsafe_accept_count"] == 0


def test_holdout_receipt_rejects_missing_metric(tmp_path):
    payload = holdout()
    del payload["qc_agreement"]
    target = tmp_path / "holdout.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="qc_agreement"):
        load_holdout_receipt(target)


def test_holdout_receipt_rejects_diagnostic_claim(tmp_path):
    payload = holdout()
    payload["diagnostic_claims"] = True
    target = tmp_path / "holdout.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="diagnostic"):
        load_holdout_receipt(target)


def test_sha256_file_matches_reference(tmp_path):
    target = tmp_path / "evidence.json"
    target.write_bytes(b"source-bound evidence\n")
    assert sha256_file(target) == hashlib.sha256(target.read_bytes()).hexdigest()


def test_manifest_is_sorted_and_does_not_hash_itself(tmp_path):
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    hashes = write_manifest(tmp_path)
    assert list(hashes) == ["a.txt", "z.txt"]
    manifest = tmp_path / "SHA256SUMS"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("  a.txt")
    assert not any(line.endswith("  SHA256SUMS") for line in lines)
    assert b"\r\n" not in manifest.read_bytes()


def test_manifest_uses_relative_posix_paths(tmp_path):
    nested = tmp_path / "screenshots"
    nested.mkdir()
    (nested / "clean.png").write_bytes(b"png")
    assert "screenshots/clean.png" in write_manifest(tmp_path)


def test_presentation_evidence_is_source_bound_and_not_self_approving(tmp_path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"judge-video")
    evidence = build_presentation_evidence(
        "a" * 40, video, 62.4, set(REQUIRED_PRESENTATION_COVERAGE)
    )
    assert evidence["source_sha"] == "a" * 40
    assert evidence["video_sha256"] == hashlib.sha256(b"judge-video").hexdigest()
    assert evidence["video_duration_seconds"] == 62.4
    assert evidence["captioned"] is True
    assert evidence["human_reviewed"] is False
    assert evidence["judge_accessible"] is False
    assert all(evidence[key] is True for key in REQUIRED_PRESENTATION_COVERAGE)


@pytest.mark.parametrize("missing", REQUIRED_PRESENTATION_COVERAGE)
def test_presentation_evidence_rejects_missing_required_scene(tmp_path, missing):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"judge-video")
    coverage = set(REQUIRED_PRESENTATION_COVERAGE) - {missing}
    with pytest.raises(ValueError, match="missing required coverage"):
        build_presentation_evidence("a" * 40, video, 30.0, coverage)


def test_shell_wrapper_preserves_linux_tmpfs_path_under_git_bash():
    wrapper = (
        Path(__file__).resolve().parents[1] / "tools" / "judge_video_capture.sh"
    ).read_text(encoding="utf-8")
    assert "MSYS_NO_PATHCONV=1 docker run -d" in wrapper
    assert "--tmpfs /tmp" in wrapper
