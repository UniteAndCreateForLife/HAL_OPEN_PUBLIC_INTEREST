import base64

import cv2
from fastapi.testclient import TestClient

from labsight.api import app
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
    assert "opencv5_verified" in response.json()


def test_analyze_png():
    ok, encoded = cv2.imencode(".png", microscopy_scene())
    assert ok
    payload = base64.b64encode(encoded.tobytes()).decode("ascii")
    response = client.post("/analyze", json={"image_base64": payload})
    assert response.status_code == 200
    body = response.json()
    assert body["trace"]
    assert "focus_variance" in body["metrics"]


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
