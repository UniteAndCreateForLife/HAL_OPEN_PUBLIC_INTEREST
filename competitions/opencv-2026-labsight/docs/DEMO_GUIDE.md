# LabSight visual demo — no cloud account required

This review surface runs against a local LabSight server or the production
container. It does not require AWS credentials. **Microscopy image-quality
control only: not diagnosis, biological identification or clinical validation.**
The interface never converts local execution into AWS/submission evidence.

## Run

From `competitions/opencv-2026-labsight/`, use the installed project environment:

```bash
python -m uvicorn labsight.api:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/`. The runtime banner reports the running server's
package, OpenCV core version and source SHA. A mixed or development environment
is visibly marked unverified; metadata is not independent deployment attestation.
The competition container remains pinned to `opencv-python==5.0.0.93`, with
OpenCV core `5.0.0`. Do not change the pin to satisfy a demo.

## Suggested demonstration sequence

1. Analyze **Clean**. Explain the capture-quality decision and measured signals.
2. Analyze **Blur** and **Exposure**. Show two distinct recapture requests.
3. Analyze **Illumination**. Read pass 1, its CLAHE decision, then the second
   visual pass and final action. Measurements shown are the actual response,
   not hard-coded success labels.
4. Run the **judge suite**. Inspect expected versus observed actions in all four
   deterministic cases; Agentic Vision proof is displayed separately.
5. Download the JSON receipt. Show its request ID, timing and runtime observation.
   It deliberately says `interactive_demo_not_aws_or_submission_evidence`.
6. Explain limitations, human review and the separately documented independent
   source evaluation. Do not turn four synthetic examples into an accuracy claim.

The scenario preview is decoded from `/demo/image/{scenario}`, which uses the
same canonical `JUDGE_SCENARIOS` parameters as the analysis and judge routes.
It displays the input capture, not a fabricated enhanced output. Uploaded images
are previewed with temporary local object URLs, revoked when replaced. Analysis
sends the selected image to the current server; do not upload sensitive material.
JSON downloads exclude image bytes, base64 data and original filenames.

## Interaction reliability

Buttons and file input are disabled while an operation is running. Requests have
a 30-second deadline and stale responses cannot overwrite newer results. HTTP
errors, non-JSON responses and missing action/trace data do not become successful
analyses. Failed requests clear previous downloadable evidence. File size/type
checks run before upload; server-side pixel/header checks remain authoritative.
The interface has keyboard focus indicators, labeled controls, live status,
responsive layout and expandable raw evidence. It has no external CDN dependency.

## Browser regression run

`tools/browser_demo_smoke.py` exercises the live UI and its HTTP contracts. It
uses Playwright as **optional development/test tooling**, not a production
dependency. In a project-local test environment with Playwright and an available
browser installed:

```bash
python tools/browser_demo_smoke.py --url http://127.0.0.1:8080 \
  --output evaluation/latest/browser-demo
```

For an existing Edge/Chromium installation, supply `--executable /path/to/browser`.
The script runs clean and two-pass scenarios, the judge suite, actual upload,
evidence download, keyboard/viewport checks, and controlled HTTP/network/JSON
failure recovery. The induced failures are explicitly recorded as test doubles;
successful analyses use the real local service. It writes JSON results and a
real UI screenshot. These are browser test artifacts, not AWS evidence or a
completed competition video. The final narrated video is still a separate task.

## Captioned judge-video rehearsal

	ools/judge_video_capture.py records the live local UI from an exact source-bound
OpenCV 5 service, adds visible presentation captions, and transcodes the browser
recording to H.264 MP4. It fails closed on source/runtime mismatch and on videos
longer than five minutes. The output also includes a SHA-256 receipt and narration
notes. Use an existing Chromium/Edge binary and local ffmpeg/ffprobe; no upload or
cloud account is required.

`ash
python tools/judge_video_capture.py --url http://127.0.0.1:18080 \
  --output evaluation/latest/judge-video --expected-source-sha GIT_SHA \
  --executable /path/to/chromium
```

The generated MP4 is a captioned **rehearsal**, not an authenticated AWS receipt or
final Devpost submission. Before final submission, review pacing/content, add or
approve narration if desired, verify judge accessibility, and preserve the <=5-minute
gate. The deterministic showcase remains separate from independent evaluation.

## Deferred cloud work

AWS authentication is `DEFERRED_BY_USER`. Do not repeatedly probe credentials,
install cloud tooling, or ask for credentials while completing this local work.
Keep the existing ECR/App Runner integration and final competition requirements
intact. Only resume that work after explicit user direction/access confirmation.
