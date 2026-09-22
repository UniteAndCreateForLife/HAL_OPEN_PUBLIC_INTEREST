from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

QCStressor = Literal[
    "native",
    "blur",
    "clipped",
    "uneven_illumination",
]


@dataclass(frozen=True)
class OpenImageSource:
    id: str
    url: str
    source_page_url: str
    license: str
    license_url: str
    attribution: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_dynamic_range(
    image: np.ndarray,
    low: int = 50,
    high: int = 190,
) -> np.ndarray:
    """Normalize globally while preserving relative channel structure."""
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("image must be a non-empty NumPy array")
    work = np.clip(image, 0, 255).astype(np.float32)
    mn = float(work.min())
    mx = float(work.max())
    if mx <= mn:
        return np.full_like(work, low, dtype=np.uint8)
    scaled = (work - mn) / (mx - mn)
    scaled = scaled * float(high - low) + float(low)
    return np.clip(scaled, 0, 255).astype(np.uint8)


def apply_qc_stressor(
    image: np.ndarray,
    stressor: QCStressor,
) -> np.ndarray:
    """Apply a deterministic capture-quality stressor to microscopy imagery.

    These transforms change image quality only. They do not create or alter
    biological or diagnostic labels.
    """
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("image must be a non-empty NumPy array")
    image = np.clip(image, 0, 255).astype(np.uint8)
    if stressor == "native":
        return image.copy()
    if stressor == "blur":
        return cv2.GaussianBlur(image, (0, 0), 5.0)
    if stressor == "clipped":
        out = image.copy()
        width = out.shape[1]
        start = width // 3
        end = max(start + 1, width // 2)
        out[:, start:end] = 255
        return out
    if stressor == "uneven_illumination":
        out = normalize_dynamic_range(
            image,
            low=50,
            high=190,
        ).astype(np.float32)
        width = out.shape[1]
        gradient = np.linspace(0.6, 1.2, width, dtype=np.float32)
        if out.ndim == 3:
            gradient = gradient[None, :, None]
        else:
            gradient = gradient[None, :]
        return np.clip(out * gradient, 0, 255).astype(np.uint8)
    raise ValueError(f"unsupported QC stressor: {stressor}")


def write_png(path: Path, image: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError(f"OpenCV failed to encode {path}")
    payload = encoded.tobytes()
    path.write_bytes(payload)
    return sha256_bytes(payload)
