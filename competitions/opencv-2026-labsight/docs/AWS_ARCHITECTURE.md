# AWS deployment architecture

Final competition deployment target:

1. Browser/demo client uploads a microscopy image to the LabSight API.
2. AWS App Runner serves an immutable Amazon ECR container over managed HTTPS.
3. The container pins OpenCV 5.0.0.93 and runs the deterministic QC toolchain.
4. Evaluation artifacts can be stored in Amazon S3; uploaded demo images are processed in memory by default.
5. App Runner/CloudWatch logs record request latency, correlated QC decisions, agent-step count, enhancement-tool use, runtime OpenCV version, and source build SHA.
6. The agent loop uses vision evidence to choose one of: accept, re-run illumination correction, request recapture, or request human review.

## CloudWatch evidence contract

Each HTTP request receives an `x-labsight-request-id` and `Server-Timing` header. The same request ID is attached to a structured `qc_decision` JSON log event containing only operational evidence: decision, source class, whether CLAHE was invoked, number of agent steps, analysis latency, OpenCV runtime, and build SHA. Raw image bytes and base64 payloads are deliberately excluded from telemetry.

For the Agentic Vision evidence capture, run the `uneven` demo case and preserve the matching response trace and `qc_decision` log. The expected trace has two perception steps: the first chooses `enhance_and_reanalyze`; OpenCV CLAHE is invoked; the second measurement determines the final action. This makes the vision-output -> tool-action dependency auditable in CloudWatch rather than relying on narration alone.

The first production slice intentionally does not send images to a general-purpose external LLM. This minimizes privacy exposure and makes the perception/action trace reproducible. LabSight remains microscopy image-quality control only and must not be presented as a clinical or biological diagnostic system.

## Evidence still required from authenticated AWS

- App Runner service URL and service ARN
- immutable ECR image digest
- `/health` response proving OpenCV 5.x, build SHA, and dependency versions
- correlated CloudWatch `http_request` + `qc_decision` events
- P50/P95 cloud latency on the frozen evaluation corpus
- deployment timestamp and region

None of those cloud-runtime claims are complete until captured from the authenticated AWS deployment.
