from labsight.agent import LabSightAgent
from labsight.metrics import compute_metrics
from labsight.synthetic import microscopy_scene


def test_blur_reduces_focus_metric():
    sharp = microscopy_scene(blur_sigma=0)
    blurred = microscopy_scene(blur_sigma=4)
    assert compute_metrics(sharp).focus_variance > compute_metrics(blurred).focus_variance * 5


def test_agent_requests_focus_recapture_for_blurred_sample():
    result = LabSightAgent().analyze(microscopy_scene(blur_sigma=5))
    assert result.status == "request_recapture_focus"


def test_agent_uses_second_vision_pass_for_uneven_illumination():
    result = LabSightAgent().analyze(microscopy_scene(illumination_gradient=1.0))
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
