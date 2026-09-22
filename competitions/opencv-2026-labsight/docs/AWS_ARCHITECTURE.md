# AWS deployment architecture

Final competition deployment target:

1. Browser/demo client uploads a microscopy image to the LabSight API.
2. AWS App Runner serves an immutable Amazon ECR container over managed HTTPS.
3. The container pins OpenCV 5.0.0.93 and runs the deterministic QC toolchain.
4. Evaluation artifacts can be stored in Amazon S3; uploaded demo images are processed in memory by default.
5. App Runner/CloudWatch logs record request latency, tool decisions, failure reasons, and QC outcomes.
6. The agent loop uses vision evidence to choose one of: accept, re-run illumination correction, request recapture, or request human review.

The first production slice intentionally does not send images to a general-purpose external LLM. This minimizes privacy exposure and makes the perception/action trace reproducible. A later optional reasoning layer may consume metrics only, not raw imagery.

## Competition evidence to capture on AWS

- OpenCV runtime version showing 5.x.
- Container image digest and pinned Python dependency lock.
- P50/P95 API latency on a fixed evaluation corpus.
- Accuracy of accept/recapture decisions on synthetically degraded and real consented microscopy images.
- CloudWatch trace demonstrating that visual metrics change a later tool call/action.
