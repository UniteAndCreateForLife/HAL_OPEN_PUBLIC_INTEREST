from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

import cv2
import numpy as np

from labsight.real_corpus import apply_qc_stressor, verify_source_sha256, write_png

USER_AGENT = "HAL-LabSight/0.1 (+OpenCV-AI-Competition-2026)"
STRESSORS = (
    ("native", None, None, None),
    (
        "blur",
        "request_recapture_focus",
        "request_recapture_focus",
        False,
    ),
    (
        "clipped",
        "request_recapture_exposure",
        "request_recapture_exposure",
        False,
    ),
    ("uneven_illumination", None, "enhance_and_reanalyze", True),
)


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:  # nosec B310
        if response.status != 200:
            raise RuntimeError(
                f"download failed with HTTP {response.status}: {url}"
            )
        return response.read()


def _decode(payload: bytes, source_id: str) -> np.ndarray:
    image = cv2.imdecode(
        np.frombuffer(payload, dtype=np.uint8),
        cv2.IMREAD_UNCHANGED,
    )
    if image is None:
        raise ValueError(
            f"{source_id}: OpenCV could not decode downloaded image"
        )
    return image


def build(catalog_path: Path, output_root: Path) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("purpose") != "image_quality_control_only":
        raise ValueError(
            "source catalog purpose must be image_quality_control_only"
        )
    sources = catalog.get("sources", [])
    if not sources:
        raise ValueError(
            "source catalog must contain at least one source"
        )

    items: list[dict] = []
    source_locks: list[dict] = []
    for source in sources:
        url = str(source["url"])
        if not url.startswith("https://"):
            raise ValueError(
                f"{source['id']}: only HTTPS source URLs are accepted"
            )
        payload = _download(url)
        source_sha256 = verify_source_sha256(
            payload, str(source.get("expected_sha256", "")), str(source["id"])
        )
        image = _decode(payload, str(source["id"]))
        source_locks.append(
            {
                "id": source["id"],
                "url": url,
                "sha256": source_sha256,
            }
        )

        for (
            stressor,
            expected_final,
            expected_first,
            expected_enhancement,
        ) in STRESSORS:
            derived = apply_qc_stressor(image, stressor)
            rel_path = (
                Path("images")
                / f"{source['id']}__{stressor}.png"
            )
            derived_sha256 = write_png(
                output_root / rel_path,
                derived,
            )
            items.append(
                {
                    "id": f"{source['id']}__{stressor}",
                    "path": rel_path.as_posix(),
                    "sha256": derived_sha256,
                    "source_url": url,
                    "source_page_url": source["source_page_url"],
                    "license": source["license"],
                    "license_url": source["license_url"],
                    "attribution": source["attribution"],
                    "parent_sha256": source_sha256,
                    "derivation": stressor,
                    "expected_qc_status": expected_final,
                    "expected_first_action": expected_first,
                    "expected_enhancement": expected_enhancement,
                }
            )

    manifest = {
        "purpose": "image_quality_control_only",
        "diagnostic_claims": False,
        "dataset": catalog.get("dataset", "BBBC038v1"),
        "source_locks": source_locks,
        "items": items,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the provenance-locked BBBC038 LabSight QC corpus"
        )
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("evaluation/real/source_catalog.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/real/generated"),
    )
    args = parser.parse_args()
    manifest = build(args.catalog, args.output)
    print(
        json.dumps(
            {
                "samples": len(manifest["items"]),
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
