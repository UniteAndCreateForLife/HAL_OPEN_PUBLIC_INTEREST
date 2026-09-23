"""Capture a source-bound, captioned local LabSight judge rehearsal video.

This tool records only an authorized LabSight URL. The resulting MP4 is local
presentation evidence, never AWS or final-submission evidence by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

EXPECTED_DISTRIBUTION = "5.0.0.93"
EXPECTED_RUNTIME = "5.0.0"
MAX_VIDEO_SECONDS = 300.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _authorized_local_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("--url must be an authorized local HTTP LabSight service")


def _validate_runtime(health: dict[str, Any], expected_source_sha: str) -> None:
    source_sha = str(health.get("source_sha", "")).lower()
    if source_sha != expected_source_sha.lower():
        raise ValueError(
            f"source SHA mismatch: {source_sha!r} != {expected_source_sha!r}"
        )
    if str(health.get("opencv_distribution_version", "")) != EXPECTED_DISTRIBUTION:
        raise ValueError(
            "demo server does not use the exact competition OpenCV distribution"
        )
    if str(health.get("opencv_runtime_version", "")) != EXPECTED_RUNTIME:
        raise ValueError(
            "demo server does not use the exact competition OpenCV core runtime"
        )
    if health.get("opencv5_verified") is not True:
        raise ValueError("demo server did not verify OpenCV 5")


def _probe_duration(ffprobe: str, path: Path) -> float:
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nk=1:nw=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(proc.stdout.strip())
    if not 0 < duration <= MAX_VIDEO_SECONDS:
        raise ValueError(
            f"video duration {duration:.3f}s is outside the <=5 minute gate"
        )
    return duration


def _overlay(page: Any, title: str, detail: str) -> None:
    page.evaluate(
        """([title, detail]) => {
          let box = document.getElementById('hal-capture-overlay');
          if (!box) {
            box = document.createElement('section');
            box.id = 'hal-capture-overlay';
            box.style.cssText = 'position:fixed;z-index:99999;left:24px;right:24px;top:18px;padding:14px 18px;border-radius:12px;background:rgba(8,15,24,.92);color:white;font:16px/1.35 system-ui;box-shadow:0 8px 30px #0008;pointer-events:none';
            document.body.appendChild(box);
          }
          box.innerHTML = `<strong style="font-size:20px">${title}</strong><br><span>${detail}</span>`;
        }""",
        [title, detail],
    )


def _pause(page: Any, seconds: float = 2.0) -> None:
    page.wait_for_timeout(int(seconds * 1000))


def _click_and_wait(page: Any, name: str, status_text: str | None = None) -> None:
    page.get_by_role("button", name=name, exact=True).click()
    if status_text:
        page.locator("#status").get_by_text(status_text, exact=False).wait_for(
            timeout=15000
        )
    page.wait_for_timeout(900)


def capture(
    *,
    url: str,
    output: Path,
    expected_source_sha: str,
    executable: str,
    ffmpeg: str,
    ffprobe: str,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    _authorized_local_url(url)
    output.mkdir(parents=True, exist_ok=True)
    raw_dir = output / "raw-video"
    raw_dir.mkdir(exist_ok=True)
    stages: list[dict[str, Any]] = []
    started = time.monotonic()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, executable_path=executable, args=["--disable-gpu"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(raw_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        video = page.video
        page.goto(url, wait_until="networkidle")
        health_response = context.request.get(url.rstrip("/") + "/health")
        if not health_response.ok:
            raise RuntimeError(f"health endpoint failed: HTTP {health_response.status}")
        health = health_response.json()
        _validate_runtime(health, expected_source_sha)

        _overlay(
            page,
            "HAL LabSight",
            "Microscopy image-quality control only — local exact OpenCV 5 judge rehearsal",
        )
        _pause(page, 3.0)
        stages.append(
            {"stage": "runtime", "elapsed_seconds": time.monotonic() - started}
        )

        _overlay(
            page,
            "Clean capture",
            "Measured focus, exposure and illumination signals lead to ACCEPT",
        )
        _click_and_wait(page, "Analyze clean")
        if page.locator("#decision").inner_text().strip() != "Accept capture":
            raise RuntimeError("clean scenario did not produce the expected decision")
        _pause(page, 3.0)
        stages.append({"stage": "clean", "elapsed_seconds": time.monotonic() - started})

        _overlay(
            page,
            "Blurred capture",
            "The QC policy requests recapture for focus instead of hiding the defect",
        )
        _click_and_wait(page, "Analyze blurred")
        if "focus" not in page.locator("#decision").inner_text().lower():
            raise RuntimeError("blurred scenario did not request focus recapture")
        _pause(page, 3.0)
        stages.append(
            {"stage": "blurred", "elapsed_seconds": time.monotonic() - started}
        )
        _overlay(
            page,
            "Clipped exposure",
            "The same policy separates exposure failure from blur and requests a new capture",
        )
        _click_and_wait(page, "Analyze clipped")
        if "exposure" not in page.locator("#decision").inner_text().lower():
            raise RuntimeError("clipped scenario did not request exposure recapture")
        _pause(page, 3.0)
        stages.append(
            {"stage": "clipped", "elapsed_seconds": time.monotonic() - started}
        )

        _overlay(
            page,
            "Agentic Vision",
            "Uneven illumination triggers CLAHE, a second visual pass, then a new action",
        )
        _click_and_wait(page, "Analyze uneven")
        if "2 perception passes" not in page.locator("#status").inner_text():
            raise RuntimeError("uneven scenario did not execute two perception passes")
        if "Run CLAHE and re-analyze" not in page.locator("#trace").inner_text():
            raise RuntimeError("uneven scenario did not expose the CLAHE tool action")
        _pause(page, 4.0)
        stages.append(
            {"stage": "agentic_vision", "elapsed_seconds": time.monotonic() - started}
        )

        _overlay(
            page,
            "Four-scenario judge suite",
            "Expected and observed actions are checked live; synthetic cases are not an accuracy claim",
        )
        _click_and_wait(page, "Run judge suite")
        status = page.locator("#status").inner_text()
        if (
            "Judge suite: PASS" not in status
            or "Agentic Vision demonstrated" not in status
        ):
            raise RuntimeError("judge suite did not prove the expected live behavior")
        _pause(page, 5.0)
        stages.append(
            {"stage": "judge_suite", "elapsed_seconds": time.monotonic() - started}
        )
        _overlay(
            page,
            "Evidence boundary",
            "Source-bound local demo only — not AWS, not clinical validation, not a final submission receipt",
        )
        _pause(page, 4.0)
        stages.append(
            {"stage": "limitations", "elapsed_seconds": time.monotonic() - started}
        )
        context.close()
        browser.close()
        if video is None:
            raise RuntimeError("Playwright did not create a video handle")
        raw_path = Path(video.path())

    mp4 = output / "HAL_LABSIGHT_JUDGE_REHEARSAL.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(raw_path),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(mp4),
        ],
        check=True,
    )
    duration = _probe_duration(ffprobe, mp4)
    receipt = {
        "schema_version": "1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_scope": "local_captioned_judge_rehearsal_not_aws_or_submission_evidence",
        "diagnostic_claims": False,
        "source_git_sha": expected_source_sha,
        "health": health,
        "video": {
            "path": str(mp4),
            "sha256": _sha256(mp4),
            "duration_seconds": duration,
            "width": 1280,
            "height": 720,
            "max_allowed_seconds": MAX_VIDEO_SECONDS,
        },
        "stages": stages,
    }
    (output / "judge-video-receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    narration = """# HAL LabSight judge rehearsal narration

This captioned local rehearsal demonstrates microscopy image-quality control only.
Show the exact OpenCV 5 runtime, then the clean, blur, clipped-exposure and uneven-
illumination scenarios. Emphasize that the uneven case changes action after a CLAHE
tool call and second visual pass. The four-case judge suite is deterministic showcase
evidence, not a general accuracy claim. Close by stating that independent evaluation
contains preserved failures, AWS evidence remains separate, and LabSight makes no
diagnostic, prognostic, treatment or biological-identification claim.
"""
    (output / "NARRATION.md").write_text(narration, encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:18080")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    parser.add_argument("--ffprobe", default=shutil.which("ffprobe") or "ffprobe")
    args = parser.parse_args(argv)
    receipt = capture(
        url=args.url,
        output=args.output,
        expected_source_sha=args.expected_source_sha,
        executable=args.executable,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
    )
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
