import cv2

from labsight.agent import LabSightAgent
from labsight.metrics import compute_metrics
from labsight.real_corpus import apply_qc_stressor
from labsight.synthetic import microscopy_scene


def test_blur_reduces_focus_metric():
    sharp = microscopy_scene(blur_sigma=0)
    blurred = microscopy_scene(blur_sigma=4)
    assert compute_metrics(sharp).focus_variance > compute_metrics(blurred).focus_variance * 5


def test_focus_metric_resists_smooth_illumination_gradient():
    sharp = microscopy_scene(seed=3)
    uneven = apply_qc_stressor(sharp, "uneven_illumination")
    sharp_focus = compute_metrics(sharp).focus_variance
    uneven_focus = compute_metrics(uneven).focus_variance
    assert uneven_focus > sharp_focus * 0.50


def test_agent_requests_focus_recapture_for_blurred_sample():
    result = LabSightAgent().analyze(microscopy_scene(blur_sigma=5))
    assert result.status == "request_recapture_focus"
    assert result.trace[0].decision == "request_recapture_focus"


def test_agent_uses_second_vision_pass_for_uneven_illumination():
    image = microscopy_scene(illumination_gradient=1.0)
    result = LabSightAgent().analyze(image)
    assert len(result.trace) == 2
    assert result.trace[0].decision == "enhance_and_reanalyze"
    assert result.used_enhancement is True


def test_agent_rejects_clipped_exposure():
    result = LabSightAgent().analyze(microscopy_scene(clip_highlights=True))
    assert result.status == "request_recapture_exposure"


def test_object_count_is_nonzero_on_synthetic_scene():
    metrics = compute_metrics(microscopy_scene(cells=30))
    assert metrics.object_count > 5
    assert 0 < metrics.foreground_fraction < 0.55


def test_foreground_segmentation_is_stable_after_illumination_correction():
    from labsight.metrics import improve_illumination

    clean = compute_metrics(microscopy_scene(seed=1))
    corrected = compute_metrics(
        improve_illumination(microscopy_scene(seed=1, illumination_gradient=1.0))
    )
    assert clean.foreground_fraction < 0.10
    assert corrected.foreground_fraction < 0.10
    assert abs(clean.foreground_fraction - corrected.foreground_fraction) < 0.04
