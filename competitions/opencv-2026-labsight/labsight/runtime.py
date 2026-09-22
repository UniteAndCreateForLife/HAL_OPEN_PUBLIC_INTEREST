from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import cv2

EXPECTED_OPENCV_DISTRIBUTION = "5.0.0.93"
EXPECTED_CV2_VERSION = "5.0.0"


def opencv_distribution_version() -> str | None:
    try:
        return version("opencv-python")
    except PackageNotFoundError:
        return None


def competition_runtime_info() -> dict[str, str | bool | None]:
    distribution = opencv_distribution_version()
    runtime = cv2.__version__
    verified = (
        distribution == EXPECTED_OPENCV_DISTRIBUTION
        and runtime == EXPECTED_CV2_VERSION
    )
    return {
        "opencv_distribution": distribution,
        "opencv_runtime": runtime,
        "expected_opencv_distribution": EXPECTED_OPENCV_DISTRIBUTION,
        "expected_opencv_runtime": EXPECTED_CV2_VERSION,
        "opencv5_verified": verified,
    }
