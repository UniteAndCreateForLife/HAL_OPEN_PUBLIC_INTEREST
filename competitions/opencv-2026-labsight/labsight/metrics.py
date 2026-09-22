from __future__ import annotations

from dataclasses import dataclass, asdict

import cv2
import numpy as np


@dataclass(frozen=True)
class ImageMetrics:
    focus_variance: float
    illumination_cv: float
    saturation_fraction: float
    edge_density: float
    foreground_fraction: float
    object_count: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    raise ValueError(f"Unsupported image shape: {image.shape}")


def _validate(image: np.ndarray) -> np.ndarray:
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("image must be a NumPy array")
    if image.size == 0:
        raise ValueError("image must not be empty")
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    return image


def compute_metrics(image: np.ndarray) -> ImageMetrics:
    """Compute deterministic microscopy QC metrics using OpenCV primitives."""
    image = _validate(image)
    gray = _to_gray(image)

    focus_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    sigma = max(3.0, min(gray.shape[:2]) / 18.0)
    illumination = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma, sigmaY=sigma)
    mean_illum = float(np.mean(illumination))
    illumination_cv = float(np.std(illumination) / max(mean_illum, 1.0))

    saturation_fraction = float(
        np.mean((gray <= 3).astype(np.float32) + (gray >= 252).astype(np.float32))
    )

    edges = cv2.Canny(gray, 50, 140)
    edge_density = float(np.mean(edges > 0))

    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(mask > 0) > 0.65:
        mask = cv2.bitwise_not(mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    foreground_fraction = float(np.mean(mask > 0))

    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = max(8, int(gray.size * 0.00008))
    object_count = int(
        sum(1 for i in range(1, n_labels) if int(stats[i, cv2.CC_STAT_AREA]) >= min_area)
    )

    return ImageMetrics(
        focus_variance=focus_variance,
        illumination_cv=illumination_cv,
        saturation_fraction=saturation_fraction,
        edge_density=edge_density,
        foreground_fraction=foreground_fraction,
        object_count=object_count,
    )


def improve_illumination(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE while preserving color when possible."""
    image = _validate(image)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    if image.ndim == 2:
        return clahe.apply(image)
    if image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    enhanced = improve_illumination(bgr)
    return np.dstack((enhanced, image[:, :, 3]))
