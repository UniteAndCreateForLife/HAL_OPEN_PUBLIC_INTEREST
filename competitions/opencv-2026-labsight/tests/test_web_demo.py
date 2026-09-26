"""Deterministic API and accessibility contracts for the visual review surface."""
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from labsight.api import app
from labsight.judge_demo import JUDGE_SCENARIOS
from labsight.synthetic import microscopy_scene

client = TestClient(app)


@pytest.mark.parametrize("scenario", JUDGE_SCENARIOS, ids=lambda s: s.name)
def test_preview_is_exact_same_synthetic_source_as_analysis(scenario):
    response = client.get(f"/demo/image/{scenario.name}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-labsight-request-id"]
    actual = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    expected = microscopy_scene(**scenario.params)
    assert np.array_equal(actual, expected)
    assert response.content == client.get(f"/demo/image/{scenario.name}").content


def test_preview_unknown_scenario_is_not_generated():
    assert client.get("/demo/image/missing").status_code == 404


def test_preview_encoding_failure_is_explicit(monkeypatch):
    monkeypatch.setattr("labsight.api.cv2.imencode", lambda *args: (False, None))
    response = client.get("/demo/image/clean")
    assert response.status_code == 500
    assert response.json()["detail"] == "could not encode demo preview"


def test_visual_demo_has_accessible_actions_and_evidence_controls():
    html = client.get("/").text
    for scenario in JUDGE_SCENARIOS:
        assert f'data-scenario="{scenario.name}"' in html
    for marker in ('for="file"', 'aria-describedby="upload-help"', 'aria-live="polite"',
                   'aria-atomic="true"', 'id="review"', 'id="preview"',
                   'id="download" disabled', 'Download evidence JSON', 'Run judge suite'):
        assert marker in html
    assert "interactive_demo_not_aws_or_submission_evidence" in html
    assert "Not a diagnostic system" in html
    assert "Synthetic demonstrations are regression checks" in html
    assert "not AWS or final-submission evidence" in html


def test_demo_assets_are_self_contained():
    html = client.get("/").text
    # No CDN runtime, font, telemetry, or remote script dependency for a local demo.
    assert '<script src=' not in html
    assert '<link ' not in html
    assert 'https://' not in html
    assert '.innerHTML' not in html
    assert '.textContent' in html
