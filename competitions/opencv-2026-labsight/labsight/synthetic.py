from __future__ import annotations

import cv2
import numpy as np


def microscopy_scene(
    size: int = 512,
    cells: int = 45,
    seed: int = 7,
    blur_sigma: float = 0.0,
    illumination_gradient: float = 0.0,
    clip_highlights: bool = False,
) -> np.ndarray:
    """Create deterministic microscopy-like imagery for QC regression tests."""
    rng = np.random.default_rng(seed)
    image = np.full((size, size), 175, dtype=np.float32)

    _, xx = np.mgrid[0:size, 0:size]
    if illumination_gradient:
        image += (xx / max(size - 1, 1) - 0.5) * 120.0 * illumination_gradient

    for _ in range(cells):
        x = int(rng.integers(18, size - 18))
        y = int(rng.integers(18, size - 18))
        radius = int(rng.integers(5, 14))
        value = int(rng.integers(35, 115))
        cv2.circle(image, (x, y), radius, value, -1, lineType=cv2.LINE_AA)
        if radius >= 9:
            cv2.circle(image, (x, y), max(2, radius // 3), value + 40, -1, lineType=cv2.LINE_AA)

    image += rng.normal(0, 4.0, image.shape)
    image = np.clip(image, 0, 255).astype(np.uint8)

    if blur_sigma > 0:
        image = cv2.GaussianBlur(image, (0, 0), blur_sigma)
    if clip_highlights:
        image[:, size // 3 : size // 2] = 255
    return image
