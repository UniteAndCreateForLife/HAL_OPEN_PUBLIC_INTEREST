import base64

import cv2
from fastapi.testclient import TestClient

from labsight.api import app
from labsight.synthetic import microscopy_scene

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "hal-labsight"


def test_analyze_png():
    ok, encoded = cv2.imencode(".png", microscopy_scene())
    assert ok
    payload = base64.b64encode(encoded.tobytes()).decode("ascii")
    response = client.post("/analyze", json={"image_base64": payload})
    assert response.status_code == 200
    body = response.json()
    assert body["trace"]
    assert "focus_variance" in body["metrics"]


def test_analyze_rejects_bad_payload():
    response = client.post("/analyze", json={"image_base64": "not-base64!!!"})
    assert response.status_code == 400
