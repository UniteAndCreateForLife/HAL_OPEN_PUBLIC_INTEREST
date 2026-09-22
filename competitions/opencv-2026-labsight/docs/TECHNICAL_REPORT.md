# HAL LabSight — Technical Report Draft

## Problem
Microscopy workflows can fail before analysis begins: blur, clipping, uneven illumination, and poor specimen occupancy can make downstream measurements unreliable. LabSight focuses on **capture-quality control** rather than diagnosis.

## Agentic vision loop
LabSight is deliberately auditable:

1. **Perceive** — OpenCV measures focus, illumination coefficient of variation, clipping, edge density, segmentation occupancy, and connected objects.
2. **Decide** — deterministic policy maps those observations to a QC action.
3. **Act** — accept, request focus recapture, request exposure recapture, escalate to human review, or call an OpenCV CLAHE enhancement tool.
4. **Re-perceive** — when CLAHE is selected, LabSight performs a second vision pass and makes the final action from the new observation.

This means the visual result changes a later tool call and subsequent plan; the trace is serialized for inspection.

## Evaluation design
The regression corpus generates four deterministic capture classes across multiple random seeds:

- clean → accept
- blurred → request focus recapture
- uneven illumination → run CLAHE + second visual pass, then accept when corrected
- clipped exposure → request exposure recapture

The benchmark records decision accuracy, action/tool-call accuracy, median/P95/max latency, every per-sample QC metric, OpenCV runtime version, and whether OpenCV 5 has actually been verified.

Synthetic evaluation is engineering regression evidence only. It is not clinical validation. Before final submission, add a consented/open microscopy corpus with documented provenance and failure analysis.

## Cloud target
The competition container pins OpenCV 5 and is intended for AWS ECS/Fargate behind an ALB/API endpoint, with S3 for evaluation fixtures/evidence and CloudWatch for request/latency/decision logs.

## Reproducibility
A clean clone should support:

```bash
python -m pip install -e '.[test]'
pytest
labsight-evaluate --seeds 25 --output evaluation/latest
uvicorn labsight.api:app --host 0.0.0.0 --port 8080
```

Final AWS evidence must record the container digest, OpenCV 5.x runtime, exact dependency lock, benchmark output, deployment URL/live-demo procedure, and known failures.
