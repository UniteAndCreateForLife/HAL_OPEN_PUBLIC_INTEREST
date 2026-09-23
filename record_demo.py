from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import textwrap
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from campus_mvp import default_demo_desk, demo_cases

ROOT = Path(__file__).resolve().parent
WIDTH = 1280
HEIGHT = 720
FPS = 25
SLIDE_SECONDS = 7
SOURCE_FILES = (
    "campus_mvp.py",
    "record_demo.py",
    "test_campus_mvp.py",
    "test_record_demo.py",
    "validate_package.py",
    "APPLICATION_BRIEF.md",
    "official_rules_snapshot.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_relative_path(path: Path, artifact_root: Path) -> str:
    """Return a portable artifact path and reject directory escape."""

    try:
        return path.resolve().relative_to(artifact_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("recorded artifact must remain inside its output directory") from exc


def git_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int, size: int = 30) -> int:
    face = font(size)
    chars = max(20, int(width / (size * 0.58)))
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        lines.extend(textwrap.wrap(paragraph, width=chars) or [""])
    y = xy[1]
    for line in lines:
        draw.text((xy[0], y), line, font=face, fill="white")
        y += int(size * 1.35)
    return y


def render_slide(path: Path, title: str, sections: list[tuple[str, str]]) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#111318")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 90), fill="#222833")
    draw.text((54, 25), title, font=font(40, bold=True), fill="white")
    y = 125
    for label, value in sections:
        draw.text((58, y), label, font=font(25, bold=True), fill="#9dc5ff")
        y = wrapped(draw, value, (58, y + 34), WIDTH - 116, 26) + 20
    draw.text((58, HEIGHT - 46), "HAL Campus Evidence Desk — synthetic local competition MVP", font=font(18), fill="#b7bcc6")
    image.save(path)


def build_story() -> tuple[list[dict], list[tuple[str, list[tuple[str, str]]]]]:
    desk = default_demo_desk()
    requests = demo_cases()
    results = [asdict(desk.analyze(case)) for case in requests]
    slides: list[tuple[str, list[tuple[str, str]]]] = [
        ("HAL Campus Evidence Desk", [
            ("Goal", "Evidence-backed campus support that cites policy, proposes bounded actions, and escalates uncertainty instead of guessing."),
            ("Demo scope", "Four deterministic synthetic requests. No student records, production deployment, competition submission, award, or payment."),
        ])
    ]
    for request, result in zip(requests, results, strict=True):
        evidence = result["evidence"]
        evidence_text = "none — escalated rather than invented"
        if evidence:
            evidence_text = f'{evidence[0]["doc_id"]} — {evidence[0]["title"]}'
        slides.append((f"Request: {request.request_id}", [
            ("Question", request.text),
            ("Disposition", result["disposition"]),
            ("Evidence", evidence_text),
            ("Action", ", ".join(result["suggested_actions"])),
            ("Human approval", str(result["human_approval_required"])),
            ("Audit ID", result["audit_id"]),
        ]))
    slides.append(("Bounded outcome", [
        ("What works", "Facilities routing, cited academic policy, sensitive-case human review, and fail-closed handling when evidence is absent."),
        ("Next stage", "Institution-approved corpora, role-based authorization, measured pilots, and explicit integrations only after institutional approval."),
    ]))
    return results, slides


def probe_video(path: Path, ffprobe: str) -> dict:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,width,height,pix_fmt:format=duration", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    raw = json.loads(result.stdout)
    stream = raw["streams"][0]
    return {
        "duration_seconds": round(float(raw["format"]["duration"]), 3),
        "codec": stream["codec_name"],
        "width": stream["width"],
        "height": stream["height"],
        "pixel_format": stream["pix_fmt"],
    }


def write_video(slides: list[tuple[str, list[tuple[str, str]]]], output: Path, ffmpeg: str) -> None:
    frames = output.parent / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    slide_paths: list[Path] = []
    for index, (title, sections) in enumerate(slides):
        path = frames / f"slide-{index:02d}.png"
        render_slide(path, title, sections)
        slide_paths.append(path)
    concat = output.parent / "slides.ffconcat"
    lines = ["ffconcat version 1.0"]
    for slide in slide_paths:
        lines.append(f"file '{slide.as_posix()}'")
        lines.append(f"duration {SLIDE_SECONDS}")
    lines.append(f"file '{slide_paths[-1].as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-movflags", "+faststart", "-an", str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def source_hashes() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def build_receipt(output_dir: Path, results: list[dict], video: Path, ffprobe: str) -> dict:
    return {
        "competition": "Global Smart Campus Technology Innovation Challenge 2026",
        "source_commit": git_head(),
        "source_sha256": source_hashes(),
        "video": artifact_relative_path(video, output_dir),
        "video_sha256": sha256(video),
        "video_probe": probe_video(video, ffprobe),
        "demo_results": results,
        "scope": "synthetic_local_recorded_mvp_not_submission_or_production_evidence",
        "claims": {
            "submitted": False,
            "finalist": False,
            "awarded": False,
            "paid": False,
            "production_deployed": False,
            "real_student_data_used": False,
            "institutional_pilot": False,
        },
    }


def verify_receipt(path: Path, ffprobe: str) -> dict:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt["source_commit"] != git_head():
        raise ValueError("source commit drift")
    for name, expected in receipt["source_sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"source hash drift: {name}")
    video = Path(receipt["video"])
    if not video.is_absolute():
        video = path.resolve().parent / video
    if sha256(video) != receipt["video_sha256"]:
        raise ValueError("video SHA-256 mismatch")
    if probe_video(video, ffprobe) != receipt["video_probe"]:
        raise ValueError("video probe mismatch")
    if any(receipt["claims"].values()):
        raise ValueError("receipt contains unsupported positive claim")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the HAL Campus recorded MVP demo")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-receipt", type=Path)
    args = parser.parse_args()
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("ffmpeg and ffprobe are required")
    if args.verify_receipt:
        receipt = verify_receipt(args.verify_receipt, ffprobe)
        print(json.dumps({"status": "PASS", "source_commit": receipt["source_commit"], "video_sha256": receipt["video_sha256"]}, sort_keys=True))
        return 0
    if not args.output_dir:
        parser.error("provide --output-dir or --verify-receipt")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    results, slides = build_story()
    video = output_dir / "HAL_CAMPUS_EVIDENCE_DESK_DEMO.mp4"
    write_video(slides, video, ffmpeg)
    receipt = build_receipt(output_dir, results, video, ffprobe)
    receipt_path = output_dir / "recorded-demo-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verify_receipt(receipt_path, ffprobe)
    print(json.dumps({"status": "PASS", "receipt": str(receipt_path), "receipt_sha256": sha256(receipt_path), "video": str(video), "video_sha256": receipt["video_sha256"], **receipt["video_probe"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
