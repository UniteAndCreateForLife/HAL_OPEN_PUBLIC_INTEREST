import labsight.runtime as runtime


def test_competition_runtime_requires_distribution_and_core(monkeypatch):
    monkeypatch.setattr(
        runtime, "opencv_distribution_version", lambda: "5.0.0.93"
    )
    monkeypatch.setattr(runtime.cv2, "__version__", "5.0.0")
    assert runtime.competition_runtime_info()["opencv5_verified"] is True


def test_mixed_installation_is_not_verified(monkeypatch):
    monkeypatch.setattr(
        runtime, "opencv_distribution_version", lambda: "4.13.0.92"
    )
    monkeypatch.setattr(runtime.cv2, "__version__", "5.0.0")
    info = runtime.competition_runtime_info()
    assert info["opencv5_verified"] is False
    assert info["opencv_distribution"] == "4.13.0.92"
    assert info["opencv_runtime"] == "5.0.0"


def test_wrong_core_is_not_verified(monkeypatch):
    monkeypatch.setattr(
        runtime, "opencv_distribution_version", lambda: "5.0.0.93"
    )
    monkeypatch.setattr(runtime.cv2, "__version__", "5.1.0")
    assert runtime.competition_runtime_info()["opencv5_verified"] is False
