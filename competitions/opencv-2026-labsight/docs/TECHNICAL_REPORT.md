# HAL LabSight — Technical Report Draft

## Problem
Microscopy workflows can fail before analysis begins: blur, clipping, uneven illumination, and poor specimen occupancy can make downstream measurements unreliable. LabSight focuses on **capture-quality control** rather than diagnosis.

## Agentic vision loop
LabSight is deliberately auditable:

1. **Perceive** — OpenCV measures CLAHE-normalized Laplacian focus, illumination coefficient of variation, clipping, edge density, segmentation occupancy, and connected objects.
2. **Decide** — deterministic policy maps those observations to a QC action.
3. **Act** — accept, request focus recapture, request exposure recapture, escalate to human review, or call an OpenCV CLAHE enhancement tool.
4. **Re-perceive** — when CLAHE is selected, LabSight performs a second vision pass and makes the final action from the new observation.

This means the visual result changes a later tool call and subsequent plan; the trace is serialized for inspection.

## Judge-facing live evidence
`GET /demo/judge` executes clean, severe-blur, uneven-illumination, and clipped-exposure scenarios against the running service. The response compares expected and observed first/final actions, preserves each serialized trace, and exposes source/runtime provenance. The uneven case is the compact Agentic Vision proof: the first OpenCV observation selects CLAHE, a second OpenCV observation is produced, and that second observation determines the final action. The response is deliberately labeled `live_runtime_demo_not_aws_by_itself`; it cannot satisfy AWS deployment evidence without an authenticated App Runner deployment and CloudWatch evidence.

## Evaluation design
The regression corpus generates four deterministic capture classes across multiple random seeds: clean, blurred, uneven illumination, and clipped exposure. The benchmark records decision accuracy, action/tool-call accuracy, median/P95/max latency, per-sample QC metrics, OpenCV runtime version, and whether OpenCV 5 has actually been verified.

Synthetic evaluation is engineering regression evidence only. It is not clinical validation. The real-image path uses five CC0 BBBC038 example images, frozen source SHA-256 locks, deterministic QC stressors, and separate final-state/action/enhancement failure analysis. Final scoring still must be repeated on the authenticated AWS/OpenCV 5 competition image.

## Input safety and failure handling
The public `/analyze` endpoint is fail-closed before OpenCV decode: only PNG/JPEG are accepted, encoded payloads are capped at 8 MiB, declared dimensions are limited to 8192 pixels per axis and 16 megapixels total, and decoded dimensions must match the encoded header. Oversized or unsupported inputs are rejected before `cv2.imdecode`, reducing decompression/resource-exhaustion risk and protecting AWS cost/reliability. The active limits are exposed by `/health` for reproducibility and operator review.

## Cloud target
The competition container pins `opencv-python==5.0.0.93` (OpenCV 5) and is intended for AWS App Runner from an immutable ECR image, with S3 reserved for evaluation fixtures/evidence and CloudWatch/App Runner logs for request/latency/decision observability.

## Reproducibility

```bash
python -m pip install -e '.[test]'
pytest
labsight-evaluate --seeds 25 --output evaluation/latest
uvicorn labsight.api:app --host 0.0.0.0 --port 8080
```

Final AWS evidence must record the container digest, `opencv-python==5.0.0.93`, `cv2.__version__==5.0.0`, benchmark output, deployment URL/live-demo procedure, and known failures.
