import base64
import struct

import cv2
import pytest
from fastapi.testclient import TestClient

import labsight.api as api_module
from labsight.api import app
from labsight.image_safety import (
    MAX_ENCODED_BYTES,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
    ImageSafetyError,
    inspect_image_bytes,
)
from labsight.synthetic import microscopy_scene

client = TestClient(app)


def _png_header(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height)


def test_png_and_jpeg_headers_are_accepted():
    image = microscopy_scene()
    for suffix in (".png", ".jpg"):
        ok, encoded = cv2.imencode(suffix, image)
        assert ok
        header = inspect_image_bytes(encoded.tobytes())
        assert header.width == image.shape[1]
        assert header.height == image.shape[0]
        assert header.format in {"png", "jpeg"}


def test_unsupported_codec_is_rejected():
    with pytest.raises(ImageSafetyError) as exc:
        inspect_image_bytes(b"GIF89a" + b"\x00" * 32)
    assert exc.value.status_code == 415


def test_declared_dimensions_are_limited_before_decode():
    with pytest.raises(ImageSafetyError) as exc:
        inspect_image_bytes(_png_header(MAX_IMAGE_DIMENSION + 1, 1))
    assert exc.value.status_code == 413


def test_declared_pixel_count_is_limited_before_decode():
    side = int(MAX_IMAGE_PIXELS ** 0.5) + 1
    with pytest.raises(ImageSafetyError) as exc:
        inspect_image_bytes(_png_header(side, side))
    assert exc.value.status_code == 413


def test_api_rejects_oversized_base64_before_decode(monkeypatch):
    monkeypatch.setattr(api_module, "MAX_BASE64_CHARS", 8)
    called = False

    def _should_not_decode(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("decoder should not run")

    monkeypatch.setattr(api_module.cv2, "imdecode", _should_not_decode)
    response = client.post("/analyze", json={"image_base64": "A" * 12})
    assert response.status_code == 413
    assert called is False


def test_api_rejects_png_dimension_bomb_before_decode(monkeypatch):
    called = False

    def _should_not_decode(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("decoder should not run")

    monkeypatch.setattr(api_module.cv2, "imdecode", _should_not_decode)
    payload = base64.b64encode(_png_header(MAX_IMAGE_DIMENSION + 1, 1)).decode("ascii")
    response = client.post("/analyze", json={"image_base64": payload})
    assert response.status_code == 413
    assert called is False


def test_health_publishes_input_safety_contract():
    body = client.get("/health").json()
    assert body["accepted_image_formats"] == "PNG,JPEG"
    assert body["max_encoded_bytes"] == MAX_ENCODED_BYTES
    assert body["max_image_pixels"] == MAX_IMAGE_PIXELS
    assert body["max_image_dimension"] == MAX_IMAGE_DIMENSION
