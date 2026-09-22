import base64
import json
import logging

import cv2
from fastapi.testclient import TestClient

from labsight.api import EXPECTED_OPENCV_VERSION, _competition_runtime_verified, app
from labsight.runtime import EXPECTED_CV2_VERSION
from labsight.synthetic import microscopy_scene

client = TestClient(app)


def test_home_demo_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "HAL LabSight" in response.text
    assert "Analyze uneven" in response.text
    assert response.headers["x-labsight-request-id"]
    assert "labsight;dur=" in response.headers["server-timing"]


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "hal-labsight"
    body = response.json()
    assert body["expected_opencv"] == EXPECTED_OPENCV_VERSION
    assert body["opencv_distribution"]
    assert body["expected_cv2"] == EXPECTED_CV2_VERSION
    assert isinstance(body["opencv5_verified"], bool)
    assert body["numpy"]
    assert body["build_sha"]


def test_competition_runtime_verification_is_exact():
    assert _competition_runtime_verified("5.0.0.93", "5.0.0") is True
    assert _competition_runtime_verified("4.13.0.92", "5.0.0") is False
    assert _competition_runtime_verified("5.0.0.92", "5.0.0") is False
    assert _competition_runtime_verified("5.0.0.93", "5.1.0") is False
    assert _competition_runtime_verified(None, "5.0.0") is False


def test_analyze_png():
    ok, encoded = cv2.imencode(".png", microscopy_scene())
    assert ok
    payload = base64.b64encode(encoded.tobytes()).decode("ascii")
    response = client.post("/analyze", json={"image_base64": payload})
    assert response.status_code == 200
    body = response.json()
    assert body["trace"]
    assert "focus_variance" in body["metrics"]


def test_qc_decision_log_is_correlated_and_image_free(caplog):
    caplog.set_level(logging.INFO, logger="labsight.api")
    response = client.get("/demo/analyze/uneven", headers={"x-request-id": "evidence-123"})
    assert response.status_code == 200
    events = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    decisions = [event for event in events if event.get("event") == "qc_decision"]
    assert len(decisions) == 1
    event = decisions[0]
    assert event["request_id"] == "evidence-123"
    assert event["source"] == "demo:uneven"
    assert event["used_enhancement"] is True
    assert event["agent_steps"] == 2
    assert event["decision"] == response.json()["status"]
    assert "image" not in event
    assert "image_base64" not in event


def test_demo_uneven_has_second_agent_step():
    response = client.get("/demo/analyze/uneven")
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "uneven"
    assert body["used_enhancement"] is True
    assert len(body["trace"]) == 2
    assert body["trace"][0]["decision"] == "enhance_and_reanalyze"


def test_demo_unknown_is_404():
    assert client.get("/demo/analyze/nope").status_code == 404


def test_analyze_rejects_bad_payload():
    response = client.post("/analyze", json={"image_base64": "not-base64!!!"})
    assert response.status_code == 400
