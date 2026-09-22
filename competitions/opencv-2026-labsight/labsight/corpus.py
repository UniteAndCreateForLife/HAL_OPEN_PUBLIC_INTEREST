from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from .agent import LabSightAgent


@dataclass(frozen=True)
class CorpusItem:
    id: str
    path: str
    sha256: str
    source_url: str
    license: str
    attribution: str
    expected_qc_status: str | None = None


def load_manifest(path: Path) -> list[CorpusItem]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("purpose") != "image_quality_control_only":
        raise ValueError("manifest purpose must be image_quality_control_only")
    items = [CorpusItem(**item) for item in data.get("items", [])]
    if not items:
        raise ValueError("manifest must contain at least one item")
    for item in items:
        if not item.source_url.startswith(("https://", "http://")):
            raise ValueError(f"{item.id}: source_url must be an HTTP(S) provenance URL")
        if not item.license.strip() or not item.attribution.strip():
            raise ValueError(f"{item.id}: license and attribution are required")
        if len(item.sha256) != 64:
            raise ValueError(f"{item.id}: sha256 must be a 64-character digest")
    return items


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_corpus(manifest_path: Path, image_root: Path) -> dict:
    """Evaluate provenance-verified microscopy images without diagnostic inference."""
    items = load_manifest(manifest_path)
    agent = LabSightAgent()
    rows: list[dict] = []

    for item in items:
        image_path = (image_root / item.path).resolve()
        root = image_root.resolve()
        if root not in image_path.parents and image_path != root:
            raise ValueError(f"{item.id}: image path escapes image_root")
        if not image_path.is_file():
            raise FileNotFoundError(f"{item.id}: missing image {image_path}")
        actual_sha = _sha256(image_path)
        if actual_sha.lower() != item.sha256.lower():
            raise ValueError(f"{item.id}: SHA256 mismatch")
        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError(f"{item.id}: OpenCV could not decode image")

        start = time.perf_counter()
        result = agent.analyze(image)
        latency_ms = (time.perf_counter() - start) * 1000.0
        expected = item.expected_qc_status
        rows.append({
            "id": item.id,
            "source_url": item.source_url,
            "license": item.license,
            "attribution": item.attribution,
            "sha256": actual_sha,
            "expected_qc_status": expected,
            "actual_qc_status": result.status,
            "matches_expected": None if expected is None else result.status == expected,
            "used_enhancement": result.used_enhancement,
            "trace_steps": len(result.trace),
            "latency_ms": round(latency_ms, 3),
            "metrics": result.metrics.to_dict(),
        })

    scored = [row for row in rows if row["matches_expected"] is not None]
    return {
        "purpose": "image_quality_control_only",
        "diagnostic_claims": False,
        "samples": len(rows),
        "scored_samples": len(scored),
        "qc_agreement": None if not scored else sum(bool(r["matches_expected"]) for r in scored) / len(scored),
        "opencv": cv2.__version__,
        "items": rows,
    }
