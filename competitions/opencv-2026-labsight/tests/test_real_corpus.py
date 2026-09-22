import pytest

from labsight.agent import LabSightAgent
from labsight.real_corpus import (
    apply_qc_stressor,
    normalize_dynamic_range,
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
