from __future__ import annotations

import hashlib
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from .agent import LabSightAgent

ALLOWED_QC_STATUSES = {
    "accept",
    "request_recapture_focus",
    "request_recapture_exposure",
    "human_review",
}


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
    seen_ids: set[str] = set()
    for item in items:
        if not item.id.strip() or item.id in seen_ids:
            raise ValueError(f"duplicate or empty corpus id: {item.id!r}")
        seen_ids.add(item.id)
        if not item.source_url.startswith(("https://", "http://")):
            raise ValueError(f"{item.id}: source_url must be an HTTP(S) provenance URL")
        if not item.license.strip() or not item.attribution.strip():
            raise ValueError(f"{item.id}: license and attribution are required")
        if len(item.sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in item.sha256):
            raise ValueError(f"{item.id}: sha256 must be a 64-character hexadecimal digest")
        if item.expected_qc_status is not None and item.expected_qc_status not in ALLOWED_QC_STATUSES:
            raise ValueError(f"{item.id}: unsupported expected_qc_status {item.expected_qc_status!r}")
    return items


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _failure_analysis(rows: list[dict]) -> dict:
    scored = [row for row in rows if row["matches_expected"] is not None]
    failures = [row for row in scored if not row["matches_expected"]]
    confusion: dict[str, dict[str, int]] = {}
    per_expected: dict[str, dict[str, float | int]] = {}
    for row in scored:
        expected = str(row["expected_qc_status"])
        actual = str(row["actual_qc_status"])
        confusion.setdefault(expected, {})[actual] = confusion.setdefault(expected, {}).get(actual, 0) + 1
    for expected in sorted({str(row["expected_qc_status"]) for row in scored}):
        group = [row for row in scored if row["expected_qc_status"] == expected]
        matched = sum(bool(row["matches_expected"]) for row in group)
        per_expected[expected] = {
            "samples": len(group),
            "correct": matched,
            "recall": matched / len(group),
        }
    return {
        "failure_count": len(failures),
        "failure_rate": None if not scored else len(failures) / len(scored),
        "failure_ids": [str(row["id"]) for row in failures],
        "confusion_matrix": confusion,
        "per_expected_status": per_expected,
    }


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
    latencies = [float(row["latency_ms"]) for row in rows]
    sorted_latency = sorted(latencies)
    p95_index = min(len(sorted_latency) - 1, max(0, int(len(sorted_latency) * 0.95) - 1))
    major = int(cv2.__version__.split(".")[0])
    return {
        "purpose": "image_quality_control_only",
        "diagnostic_claims": False,
        "samples": len(rows),
        "scored_samples": len(scored),
        "qc_agreement": None if not scored else sum(bool(r["matches_expected"]) for r in scored) / len(scored),
        "latency_ms": {
            "median": round(statistics.median(latencies), 3),
            "p95": round(sorted_latency[p95_index], 3),
            "max": round(max(latencies), 3),
        },
        "runtime": {
            "opencv": cv2.__version__,
            "opencv5_verified": major >= 5,
        },
        "failure_analysis": _failure_analysis(rows),
        "items": rows,
    }
