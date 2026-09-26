import pytest

from labsight.agent import LabSightAgent
from labsight.real_corpus import (
    apply_qc_stressor,
    normalize_dynamic_range,
    verify_source_sha256,
)
from labsight.synthetic import microscopy_scene


def test_blur_stressor_drives_focus_recapture():
    result = LabSightAgent().analyze(
        apply_qc_stressor(microscopy_scene(), "blur")
    )
    assert result.trace[0].decision == "request_recapture_focus"
    assert result.status == "request_recapture_focus"


def test_clipped_stressor_drives_exposure_recapture():
    result = LabSightAgent().analyze(
        apply_qc_stressor(microscopy_scene(), "clipped")
    )
    assert result.trace[0].decision == "request_recapture_exposure"
    assert result.status == "request_recapture_exposure"


def test_uneven_stressor_drives_second_opencv_pass():
    result = LabSightAgent().analyze(
        apply_qc_stressor(
            microscopy_scene(),
            "uneven_illumination",
        )
    )
    assert result.trace[0].decision == "enhance_and_reanalyze"
    assert result.used_enhancement is True
    assert len(result.trace) == 2


def test_severe_blur_still_wins_over_illumination_enhancement():
    blurred = microscopy_scene(blur_sigma=5)
    uneven_blurred = apply_qc_stressor(blurred, "uneven_illumination")
    result = LabSightAgent().analyze(uneven_blurred)
    assert result.trace[0].decision == "request_recapture_focus"
    assert result.used_enhancement is False


def test_dynamic_range_normalization_avoids_artificial_clipping():
    normalized = normalize_dynamic_range(microscopy_scene())
    assert normalized.min() >= 50
    assert normalized.max() <= 190


def test_unknown_stressor_fails_closed():
    with pytest.raises(ValueError, match="unsupported QC stressor"):
        apply_qc_stressor(
            microscopy_scene(),
            "diagnostic_magic",  # type: ignore[arg-type]
        )


def test_source_sha256_lock_accepts_frozen_bytes():
    payload = b"abc"
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert verify_source_sha256(payload, expected, "fixture") == expected


def test_source_sha256_lock_rejects_upstream_drift():
    with pytest.raises(ValueError, match="source SHA256 drift"):
        verify_source_sha256(b"changed", "0" * 64, "fixture")


def test_source_sha256_lock_requires_valid_digest():
    with pytest.raises(ValueError, match="expected_sha256 must be"):
        verify_source_sha256(b"abc", "not-a-lock", "fixture")
