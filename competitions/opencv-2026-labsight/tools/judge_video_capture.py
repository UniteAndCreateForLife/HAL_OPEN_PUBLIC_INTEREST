"""Record a source-bound LabSight judge demo from a real owned endpoint.

Playwright drives the shipped UI; the recorder never injects successful
responses.  The resulting package is local/CI demonstration evidence, not AWS
deployment or competition-submission evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

EXPECTED_DISTRIBUTION = "5.0.0.93"
EXPECTED_RUNTIME = "5.0.0"
EXPECTED_ACTIONS = {
    "clean": ("accept", "accept"),
    "blurred": ("request_recapture_focus", "request_recapture_focus"),
    "clipped": ("request_recapture_exposure", "request_recapture_exposure"),
    "uneven": ("enhance_and_reanalyze", "accept"),
}
REQUIRED_PRESENTATION_COVERAGE = (
    "shows_team",
    "shows_application",
    "shows_architecture",
    "shows_principal_results",
)


@dataclass(frozen=True)
class Caption:
    start: float
    end: float
    title: str
    body: str


def validate_health(health: dict[str, Any], source_sha: str) -> None:
    if health.get("source_sha") != source_sha or health.get("build_sha") != source_sha:
        raise ValueError("live source/build SHA does not match --source-sha")
    if health.get("opencv_distribution_version") != EXPECTED_DISTRIBUTION:
        raise ValueError("live opencv-python distribution is not exactly 5.0.0.93")
    if health.get("opencv_runtime_version") != EXPECTED_RUNTIME:
        raise ValueError("live cv2 runtime is not exactly 5.0.0")
    if health.get("opencv5_verified") is not True:
        raise ValueError("live service did not verify the exact OpenCV 5 runtime")


def validate_analysis(name: str, result: dict[str, Any]) -> dict[str, Any]:
    expected_first, expected_final = EXPECTED_ACTIONS[name]
    trace = result.get("trace")
    if not isinstance(trace, list) or not trace:
        raise ValueError(f"{name}: missing perception-decision-action trace")
    first = trace[0].get("decision")
    final = result.get("status")
    if (first, final) != (expected_first, expected_final):
        raise ValueError(
            f"{name}: expected {(expected_first, expected_final)}, observed {(first, final)}"
        )
    if name == "uneven":
        if len(trace) != 2 or result.get("used_enhancement") is not True:
            raise ValueError("uneven: CLAHE and a second visual pass were not observed")
        if trace[1].get("decision") != final:
            raise ValueError(
                "uneven: second visual pass did not determine the final action"
            )
    return {
        "scenario": name,
        "expected_first_action": expected_first,
        "observed_first_action": first,
        "expected_final_action": expected_final,
        "observed_final_action": final,
        "trace_steps": len(trace),
        "used_enhancement": bool(result.get("used_enhancement")),
        "passed": True,
    }


def _vtt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d}.{milliseconds:03d}"


def write_captions(
    path: Path, captions: list[Caption], *, max_duration: float | None = None
) -> None:
    lines = ["WEBVTT", ""]
    for index, item in enumerate(captions, 1):
        if max_duration is not None and item.start >= max_duration:
            raise ValueError("caption starts after the recorded video ends")
        end = max(item.end, item.start + 0.25)
        if max_duration is not None:
            end = min(end, max_duration)
        lines.extend(
            [
                str(index),
                f"{_vtt_time(item.start)} --> {_vtt_time(end)}",
                f"{item.title}: {item.body}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_presentation_evidence(
    source_sha: str,
    video_path: Path,
    duration: float,
    coverage: set[str],
) -> dict[str, Any]:
    if len(source_sha) != 40 or any(
        c not in "0123456789abcdef" for c in source_sha.lower()
    ):
        raise ValueError("presentation source SHA must be a full 40-character Git SHA")
    if not video_path.is_file():
        raise ValueError("presentation video is missing")
    if not 0 < duration <= 300:
        raise ValueError("presentation video duration must be within (0, 300]")
    missing = [key for key in REQUIRED_PRESENTATION_COVERAGE if key not in coverage]
    if missing:
        raise ValueError(
            f"presentation recording missing required coverage: {', '.join(missing)}"
        )
    return {
        "source_sha": source_sha.lower(),
        "video_sha256": sha256_file(video_path),
        "video_duration_seconds": round(duration, 3),
        "captioned": True,
        "human_reviewed": False,
        "judge_accessible": False,
        **{key: True for key in REQUIRED_PRESENTATION_COVERAGE},
        "status": "draft_requires_human_review_and_judge_accessible_hosting",
    }


def write_manifest(output: Path) -> dict[str, str]:
    excluded = {"SHA256SUMS"}
    files = sorted(
        path
        for path in output.rglob("*")
        if path.is_file() and path.name not in excluded
    )
    hashes = {path.relative_to(output).as_posix(): sha256_file(path) for path in files}
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in hashes.items()),
        encoding="utf-8",
    )
    return hashes


def load_holdout_receipt(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "source_sha",
        "samples",
        "scored_samples",
        "qc_agreement",
        "final_failure_count",
        "unsafe_accept_count",
        "limitations",
    }
    missing = sorted(required - receipt.keys())
    if missing:
        raise ValueError(f"holdout receipt missing fields: {', '.join(missing)}")
    if receipt.get("diagnostic_claims") is not False:
        raise ValueError("holdout receipt must explicitly reject diagnostic claims")
    return receipt


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def transcode(webm: Path, mp4: Path) -> float:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError(
            "ffmpeg and ffprobe are required to create and verify the MP4"
        )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(webm),
            "-an",
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
        ]
    )
    probe = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(mp4),
        ]
    )
    duration = float(probe.stdout.strip())
    if duration <= 0 or duration > 300:
        raise ValueError(f"recorded MP4 duration {duration:.3f}s is outside (0, 300]")
    return duration


def record(
    url: str,
    output: Path,
    source_sha: str,
    holdout_path: Path,
    *,
    executable: str | None = None,
    pace: float = 1.0,
) -> dict[str, Any]:
    from playwright.sync_api import expect, sync_playwright

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("--url must identify an authorized HTTP(S) LabSight instance")
    if pace <= 0:
        raise ValueError("--pace must be greater than zero")
    if len(source_sha) != 40 or any(
        c not in "0123456789abcdef" for c in source_sha.lower()
    ):
        raise ValueError("--source-sha must be a full 40-character Git SHA")
    holdout = load_holdout_receipt(holdout_path)
    output.mkdir(parents=True, exist_ok=True)
    screenshots = output / "screenshots"
    screenshots.mkdir(exist_ok=True)
    captions: list[Caption] = []
    observations: list[dict[str, Any]] = []
    presentation_coverage: set[str] = set()
    started = time.monotonic()

    def elapsed() -> float:
        return time.monotonic() - started

    def pause(page: Any, seconds: float) -> None:
        page.wait_for_timeout(round(seconds * pace * 1000))

    def scene(
        page: Any,
        title: str,
        body: str,
        seconds: float = 4.0,
        *,
        coverage_key: str | None = None,
    ) -> None:
        start = elapsed()
        page.evaluate(
            """([title, body]) => {
                let card = document.getElementById('labsight-recording-card');
                if (!card) {
                    card = document.createElement('aside');
                    card.id = 'labsight-recording-card';
                    card.setAttribute('aria-hidden', 'true');
                    Object.assign(card.style, {
                        position: 'fixed', zIndex: '2147483647', right: '24px', top: '20px',
                        maxWidth: '440px', padding: '16px 18px', borderRadius: '12px',
                        color: '#f8fafc', background: 'rgba(15,23,42,.94)',
                        border: '1px solid #38bdf8', boxShadow: '0 12px 34px rgba(0,0,0,.4)',
                        font: '16px/1.42 system-ui, sans-serif', pointerEvents: 'none'
                    });
                    document.body.appendChild(card);
                }
                card.replaceChildren();
                const heading = document.createElement('strong');
                heading.textContent = title;
                heading.style.display = 'block';
                heading.style.color = '#7dd3fc';
                heading.style.fontSize = '20px';
                heading.style.marginBottom = '6px';
                const copy = document.createElement('span');
                copy.textContent = body;
                card.append(heading, copy);
            }""",
            [title, body],
        )
        pause(page, seconds)
        captions.append(Caption(start, elapsed(), title, body))
        if coverage_key is not None:
            if coverage_key not in REQUIRED_PRESENTATION_COVERAGE:
                raise ValueError(f"unknown presentation coverage key: {coverage_key}")
            presentation_coverage.add(coverage_key)

    def analyze(page: Any, name: str, label: str) -> None:
        scene(
            page,
            label,
            "The shipped UI requests a live OpenCV analysis; no response is injected.",
            2.2,
        )
        page.get_by_role("button", name=f"Analyze {name}", exact=True).click()
        expect(page.locator("#status")).to_have_attribute("data-state", "complete")
        expect(page.locator("#download")).to_be_enabled()
        ui_receipt = json.loads(page.locator("#result").text_content() or "")
        result = ui_receipt["response"]
        observations.append(validate_analysis(name, result))
        scene(
            page,
            "Observed action",
            f"First: {observations[-1]['observed_first_action']}; final: {observations[-1]['observed_final_action']}.",
            3.0,
        )
        page.screenshot(path=str(screenshots / f"{name}.png"), full_page=True)

    browser_version = "unknown"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        browser_version = browser.version
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            accept_downloads=True,
            record_video_dir=str(output / "raw-video"),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()
        # Playwright starts recording with the page, so caption zero must share
        # that origin rather than include browser-launch time.
        started = time.monotonic()
        page.set_default_timeout(20_000)
        video = page.video
        page.goto(url, wait_until="networkidle")
        before = context.request.get(url.rstrip("/") + "/health")
        if not before.ok:
            raise RuntimeError("pre-recording /health request failed")
        health_before = before.json()
        validate_health(health_before, source_sha)

        scene(
            page,
            "Team",
            "UniteAndCreateForLife — Jakob Hedrich, solo builder.",
            3.0,
            coverage_key="shows_team",
        )
        scene(
            page,
            "HAL LabSight",
            "Microscopy image-quality control only — not diagnosis or biological identification.",
            4.0,
            coverage_key="shows_application",
        )
        scene(
            page,
            "Architecture",
            "OpenCV perception → policy decision → action or human recapture request; every step is traceable.",
            5.0,
            coverage_key="shows_architecture",
        )
        analyze(page, "clean", "Clean capture")
        analyze(page, "blurred", "Focus failure")
        analyze(page, "clipped", "Exposure failure")
        analyze(page, "uneven", "Agentic illumination recovery")

        page.get_by_role("button", name="Run judge suite", exact=True).click()
        expect(page.locator("#status")).to_contain_text("Judge suite: PASS")
        if page.locator("#suite article").count() != 4:
            raise ValueError("judge suite did not render all four scenarios")
        scene(
            page,
            "Judge suite: PASS",
            "Four deterministic cases verify accept, two recapture actions, and CLAHE re-analysis.",
            6.0,
        )
        page.screenshot(path=str(screenshots / "judge-suite.png"), full_page=True)

        raw = context.request.get(url.rstrip("/") + "/demo/image/clean").body()
        page.locator("#file").set_input_files(
            {"name": "synthetic-demo-input.png", "mimeType": "image/png", "buffer": raw}
        )
        page.get_by_role("button", name="Analyze uploaded image", exact=True).click()
        expect(page.locator("#status")).to_have_attribute("data-state", "complete")
        expect(page.locator("#decision")).to_have_text("Accept capture")
        with page.expect_download() as transfer:
            page.get_by_role(
                "button", name="Download evidence JSON", exact=True
            ).click()
        downloaded = output / "observed-ui-evidence.json"
        transfer.value.save_as(downloaded)
        download_payload = json.loads(downloaded.read_text(encoding="utf-8"))
        serialized = json.dumps(download_payload)
        if "image_base64" in serialized or "synthetic-demo-input" in serialized:
            raise ValueError(
                "downloaded evidence leaked image bytes or the local filename"
            )
        scene(
            page,
            "Evidence export",
            "A real upload and evidence download preserve request/runtime metadata without image bytes or filenames.",
            5.0,
        )

        scene(
            page,
            "Principal results — independent-source challenge",
            f"{holdout['scored_samples']} scored stressor samples: {holdout['qc_agreement']:.1%} QC agreement, "
            f"{holdout['final_failure_count']} failures, {holdout['unsafe_accept_count']} unsafe accepts.",
            7.0,
            coverage_key="shows_principal_results",
        )
        scene(
            page,
            "Limits and human control",
            "Controlled stressors are not expert ground truth or clinical validation. Review failures; recapture when requested.",
            6.0,
        )
        scene(
            page,
            "Reproducible evidence",
            "Source-bound OpenCV 5 container, deterministic tests, receipts and hashes. This recording is not AWS evidence.",
            4.0,
        )

        after = context.request.get(url.rstrip("/") + "/health")
        if not after.ok:
            raise RuntimeError("post-recording /health request failed")
        health_after = after.json()
        validate_health(health_after, source_sha)
        context.close()
        webm_source = Path(video.path())
        browser.close()

    webm = output / "labsight-judge-demo.webm"
    shutil.move(str(webm_source), webm)
    raw_dir = output / "raw-video"
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    mp4 = output / "labsight-judge-demo.mp4"
    duration = transcode(webm, mp4)
    write_captions(output / "labsight-judge-demo.vtt", captions, max_duration=duration)
    presentation = build_presentation_evidence(
        source_sha, mp4, duration, presentation_coverage
    )
    (output / "presentation-evidence-draft.json").write_text(
        json.dumps(presentation, indent=2) + "\n", encoding="utf-8"
    )
    receipt = {
        "schema_version": "1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_scope": "local_or_ci_exact_opencv5_demo_not_aws_or_final_submission_by_itself",
        "purpose": "microscopy_image_quality_control_only",
        "diagnostic_claims": False,
        "source_sha": source_sha,
        "runtime_before": health_before,
        "runtime_after": health_after,
        "observations": observations,
        "judge_suite_passed": True,
        "upload_and_download_exercised": True,
        "holdout_receipt": {
            "evaluated_source_sha": holdout["source_sha"],
            "samples": holdout["samples"],
            "scored_samples": holdout["scored_samples"],
            "qc_agreement": holdout["qc_agreement"],
            "final_failure_count": holdout["final_failure_count"],
            "unsafe_accept_count": holdout["unsafe_accept_count"],
            "limitations": holdout["limitations"],
        },
        "video_duration_seconds": round(duration, 3),
        "video_sha256": presentation["video_sha256"],
        "presentation": presentation,
        "audio": False,
        "captioned": True,
        "browser_version": browser_version,
        "ffmpeg_version": _run(["ffmpeg", "-version"]).stdout.splitlines()[0],
        "submission_status": "draft_recording_requires_human_narration_and_review",
    }
    (output / "recording-receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    receipt["artifact_sha256"] = write_manifest(output)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--holdout-receipt", type=Path, required=True)
    parser.add_argument(
        "--executable", help="Path to an existing Chromium or Edge executable"
    )
    parser.add_argument(
        "--pace", type=float, default=1.0, help="Scene timing multiplier (default: 1.0)"
    )
    args = parser.parse_args()
    try:
        report = record(
            args.url,
            args.output,
            args.source_sha,
            args.holdout_receipt,
            executable=args.executable,
            pace=args.pace,
        )
    except Exception as exc:
        print(
            json.dumps(
                {"passed": False, "error": f"{type(exc).__name__}: {exc}"}, indent=2
            )
        )
        return 1
    print(json.dumps({"passed": True, **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
