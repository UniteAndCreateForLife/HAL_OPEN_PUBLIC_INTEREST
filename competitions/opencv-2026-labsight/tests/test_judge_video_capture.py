import pytest

from tools.judge_video_capture import (
    EXPECTED_DISTRIBUTION,
    EXPECTED_RUNTIME,
    _authorized_local_url,
    _validate_runtime,
)


SOURCE_SHA = "a" * 40


def _health(**changes):
    value = {
        "source_sha": SOURCE_SHA,
        "opencv_distribution_version": EXPECTED_DISTRIBUTION,
        "opencv_runtime_version": EXPECTED_RUNTIME,
        "opencv5_verified": True,
    }
    value.update(changes)
    return value


def test_local_url_gate_accepts_loopback_only():
    _authorized_local_url("http://127.0.0.1:18080")
    _authorized_local_url("http://localhost:8080")
    with pytest.raises(ValueError, match="authorized local"):
        _authorized_local_url("https://example.com")


def test_runtime_gate_accepts_exact_source_and_opencv5():
    _validate_runtime(_health(), SOURCE_SHA)


def test_runtime_gate_rejects_source_mismatch():
    with pytest.raises(ValueError, match="source SHA mismatch"):
        _validate_runtime(_health(source_sha="b" * 40), SOURCE_SHA)


def test_runtime_gate_rejects_non_exact_distribution():
    with pytest.raises(ValueError, match="exact competition OpenCV distribution"):
        _validate_runtime(_health(opencv_distribution_version="4.13.0.92"), SOURCE_SHA)


def test_runtime_gate_rejects_unverified_opencv5():
    with pytest.raises(ValueError, match="did not verify OpenCV 5"):
        _validate_runtime(_health(opencv5_verified=False), SOURCE_SHA)
