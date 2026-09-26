from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from .agent import LabSightAgent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labsight",
        description="Microscopy image-quality control; not for diagnosis.",
    )
    parser.add_argument("image", type=Path, help="microscopy image to quality-check")
    parser.add_argument(
        "--output",
        type=Path,
        help="optional path for the JSON QC report; stdout is always emitted",
    )
    return parser


def analyze_path(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"image does not exist or is not a file: {path}")
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"OpenCV could not decode image: {path}")
    result = LabSightAgent().analyze(image)
    return {
        "purpose": "microscopy_image_quality_control_only",
        "diagnostic_claims": False,
        "source": str(path),
        **result.to_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        report = analyze_path(args.image)
    except ValueError as exc:
        parser.error(str(exc))

    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
