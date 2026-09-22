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
ALLOWED_AGENT_ACTIONS = ALLOWED_QC_STATUSES | {"enhance_and_reanalyze"}


@dataclass(frozen=True)
class CorpusItem:
    id: str
    path: str
    sha256: str
    source_url: str
    license: str
    attribution: str
    expected_qc_status: str | None = None
    source_page_url: str | None = None
    license_url: str | None = None
    parent_sha256: str | None = None
    derivation: str | None = None
    expected_first_action: str | None = None
    expected_enhancement: bool | None = None


def _is_http_url(value: str) -> bool:
    return value.startswith(("https://", "http://"))


def _validate_sha256(value: str, *, field: str, item_id: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError(
            f"{item_id}: {field} must be a 64-character hexadecimal digest"
        )


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
        if not _is_http_url(item.source_url):
            raise ValueError(
                f"{item.id}: source_url must be an HTTP(S) provenance URL"
            )
        if (
            item.source_page_url is not None
            and not _is_http_url(item.source_page_url)
        ):
            raise ValueError(f"{item.id}: source_page_url must be HTTP(S)")
        if item.license_url is not None and not _is_http_url(item.license_url):
            raise ValueError(f"{item.id}: license_url must be HTTP(S)")
        if not item.license.strip() or not item.attribution.strip():
            raise ValueError(
                f"{item.id}: license and attribution are required"
            )
        _validate_sha256(item.sha256, field="sha256", item_id=item.id)
        if item.parent_sha256 is not None:
            _validate_sha256(
                item.parent_sha256, field="parent_sha256", item_id=item.id
            )
        if item.derivation is not None and not item.derivation.strip():
            raise ValueError(
                f"{item.id}: derivation must be non-empty when provided"
            )
        if (
            item.expected_qc_status is not None
            and item.expected_qc_status not in ALLOWED_QC_STATUSES
        ):
            raise ValueError(
                f"{item.id}: unsupported expected_qc_status "
                f"{item.expected_qc_status!r}"
            )
        if (
            item.expected_first_action is not None
            and item.expected_first_action not in ALLOWED_AGENT_ACTIONS
        ):
            raise ValueError(
                f"{item.id}: unsupported expected_first_action "
                f"{item.expected_first_action!r}"
            )
    return items


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evaluation_id(items: list[CorpusItem]) -> str:
    """Stable ID for the exact ordered corpus/QC expectation contract."""
    contract = [
        {
            "id": item.id,
            "sha256": item.sha256.lower(),
            "expected_qc_status": item.expected_qc_status,
            "expected_first_action": item.expected_first_action,
            "expected_enhancement": item.expected_enhancement,
            "parent_sha256": (
                None
                if item.parent_sha256 is None
                else item.parent_sha256.lower()
            ),
            "derivation": item.derivation,
        }
        for item in items
    ]
    payload = json.dumps(
        contract, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _categorical_failure_analysis(
    rows: list[dict],
    expected_key: str,
    actual_key: str,
    match_key: str,
) -> dict:
    scored = [row for row in rows if row[match_key] is not None]
    failures = [row for row in scored if not row[match_key]]
    confusion: dict[str, dict[str, int]] = {}
    per_expected: dict[str, dict[str, float | int]] = {}
    for row in scored:
        expected = str(row[expected_key])
        actual = str(row[actual_key])
        bucket = confusion.setdefault(expected, {})
        bucket[actual] = bucket.get(actual, 0) + 1
    for expected in sorted({str(row[expected_key]) for row in scored}):
        group = [
            row for row in scored if str(row[expected_key]) == expected
        ]
        matched = sum(bool(row[match_key]) for row in group)
        per_expected[expected] = {
            "samples": len(group),
            "correct": matched,
            "recall": matched / len(group),
        }
    return {
        "failure_count": len(failures),
        "failure_rate": (
            None if not scored else len(failures) / len(scored)
        ),
        "failure_ids": [str(row["id"]) for row in failures],
        "confusion_matrix": confusion,
        "per_expected_status": per_expected,
    }


def _failure_analysis(rows: list[dict]) -> dict:
    final_status = _categorical_failure_analysis(
        rows,
        "expected_qc_status",
        "actual_qc_status",
        "matches_expected",
    )
    first_action = _categorical_failure_analysis(
        rows,
        "expected_first_action",
        "actual_first_action",
        "first_action_matches",
    )
    enhancement = _categorical_failure_analysis(
        rows,
        "expected_enhancement",
        "used_enhancement",
        "enhancement_matches",
    )
    return {
        **final_status,
        "first_action": first_action,
        "enhancement": enhancement,
    }


def _agreement(rows: list[dict], match_key: str) -> float | None:
    scored = [row for row in rows if row[match_key] is not None]
    if not scored:
        return None
    return sum(bool(row[match_key]) for row in scored) / len(scored)


def _combined_expectation_match(row: dict) -> bool | None:
    values = [
        row["matches_expected"],
        row["first_action_matches"],
        row["enhancement_matches"],
    ]
    present = [value for value in values if value is not None]
    return None if not present else all(bool(value) for value in present)


def evaluate_corpus(manifest_path: Path, image_root: Path) -> dict:
    """Evaluate provenance-verified microscopy images without diagnostic inference."""
    items = load_manifest(manifest_path)
    manifest_sha256 = _sha256(manifest_path)
    evaluation_id = _evaluation_id(items)
    agent = LabSightAgent()
    rows: list[dict] = []

    for item in items:
        image_path = (image_root / item.path).resolve()
        root = image_root.resolve()
        if root not in image_path.parents and image_path != root:
            raise ValueError(f"{item.id}: image path escapes image_root")
        if not image_path.is_file():
            raise FileNotFoundError(
                f"{item.id}: missing image {image_path}"
            )
        actual_sha = _sha256(image_path)
        if actual_sha.lower() != item.sha256.lower():
            raise ValueError(f"{item.id}: SHA256 mismatch")
        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError(
                f"{item.id}: OpenCV could not decode image"
            )

        start = time.perf_counter()
        result = agent.analyze(image)
        latency_ms = (time.perf_counter() - start) * 1000.0
        expected = item.expected_qc_status
        actual_first_action = result.trace[0].decision
        first_match = (
            None
            if item.expected_first_action is None
            else actual_first_action == item.expected_first_action
        )
        enhancement_match = (
            None
            if item.expected_enhancement is None
            else result.used_enhancement == item.expected_enhancement
        )
        row = {
            "id": item.id,
            "source_url": item.source_url,
            "source_page_url": item.source_page_url,
            "license": item.license,
            "license_url": item.license_url,
            "attribution": item.attribution,
            "sha256": actual_sha,
            "parent_sha256": item.parent_sha256,
            "derivation": item.derivation,
            "expected_qc_status": expected,
            "actual_qc_status": result.status,
            "matches_expected": (
                None if expected is None else result.status == expected
            ),
            "expected_first_action": item.expected_first_action,
            "actual_first_action": actual_first_action,
            "first_action_matches": first_match,
            "expected_enhancement": item.expected_enhancement,
            "used_enhancement": result.used_enhancement,
            "enhancement_matches": enhancement_match,
            "trace_steps": len(result.trace),
            "latency_ms": round(latency_ms, 3),
            "metrics": result.metrics.to_dict(),
        }
        row["combined_expectation_match"] = _combined_expectation_match(
            row
        )
        rows.append(row)

    latencies = [float(row["latency_ms"]) for row in rows]
    sorted_latency = sorted(latencies)
    p95_index = min(
        len(sorted_latency) - 1,
        max(0, int(len(sorted_latency) * 0.95) - 1),
    )
    major = int(cv2.__version__.split(".")[0])
    return {
        "purpose": "image_quality_control_only",
        "diagnostic_claims": False,
        "manifest_sha256": manifest_sha256,
        "evaluation_id": evaluation_id,
        "samples": len(rows),
        "scored_samples": sum(
            row["matches_expected"] is not None for row in rows
        ),
        "qc_agreement": _agreement(rows, "matches_expected"),
        "first_action_agreement": _agreement(
            rows, "first_action_matches"
        ),
        "enhancement_agreement": _agreement(
            rows, "enhancement_matches"
        ),
        "combined_expectation_agreement": _agreement(
            rows, "combined_expectation_match"
        ),
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
