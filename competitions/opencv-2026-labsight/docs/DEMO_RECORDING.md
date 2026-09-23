# Source-bound judge recording

This workflow records the real LabSight browser UI against the pinned production
container. It produces an original WebM, judge-compatible H.264 MP4, WebVTT
captions, screenshots, observed JSON receipts, service/build logs and SHA-256
manifest. It does not call AWS or any third-party service.

## Prerequisites

- Clean committed LabSight project tree
- Running Docker Linux engine
- Python 3.11+ with Playwright and its matching Chromium installed
- `ffmpeg` and `ffprobe`

From `competitions/opencv-2026-labsight/`:

```bash
python -m pip install playwright==1.55.0
python -m playwright install chromium
tools/judge_video_capture.sh evaluation/latest/judge-recording
```

The script refuses modified or untracked project inputs. It builds the actual
production Dockerfile with Git HEAD as `LABSIGHT_BUILD_SHA`, binds the service
only to loopback, and runs it read-only with a tmpfs, dropped capabilities,
`no-new-privileges`, two CPUs and 2 GiB memory.

The recorder verifies `/health` before and after capture, including exact
`opencv-python==5.0.0.93`, `cv2.__version__==5.0.0`, and matching source/build
SHA. It drives all four scenario buttons, verifies the uneven-illumination
CLAHE second pass, runs the judge suite, uploads a real synthetic PNG through
the UI and downloads the UI's evidence JSON. No successful response is mocked.

## Review and submission boundary

The default sequence is under five minutes. The MP4 is a captioned **draft with
no audio**. A human must inspect it, add or record narration, verify captions,
and choose a judge-accessible hosting route before final submission. Never call
the artifact an AWS deployment or a completed Devpost submission.

The independent-source slide is populated from the committed canonical holdout
receipt rather than copied metrics. It states both agreement and failures, and
retains these limitations: controlled stressor expectations are not expert QC
ground truth; derivatives sharing a source are not independent samples; and
the work is neither clinical validation nor biological identification.

`SHA256SUMS` covers every package artifact except itself. Re-run the command
after any source change; source/runtime mismatches fail closed.
