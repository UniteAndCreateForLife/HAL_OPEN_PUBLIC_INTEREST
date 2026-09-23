# AWS deployment

LabSight uses Amazon ECR + App Runner for a small, reproducible public competition endpoint. App Runner supplies managed HTTPS and service logs; the application exposes `/health`, a source build SHA, runtime dependency versions, and `Server-Timing` headers for evidence.

## Prerequisites

- AWS CLI authenticated to the competition AWS account
- Docker
- permissions for ECR, IAM roles, CloudFormation, and App Runner

## Deploy

From `competitions/opencv-2026-labsight/`:

```bash
export AWS_REGION=us-east-1
./aws/deploy.sh
```

The script creates an encrypted ECR repository with scan-on-push and immutable tags, embeds the current Git SHA into the image, pushes it, resolves the immutable digest, deploys App Runner using `repository@sha256:digest`, and prints the HTTPS demo and health URLs.

## Evidence to preserve

```bash
curl -fsS "https://SERVICE_URL/health"
aws apprunner list-services --region "$AWS_REGION"
aws ecr describe-images --repository-name hal-labsight --region "$AWS_REGION"
```

Final `/health` evidence must show the exact `opencv-python==5.0.0.93` distribution, `cv2.__version__==5.0.0`, `opencv5_verified: true`, the expected NumPy version, and matching Git `source_sha`/`build_sha` provenance. Cloud deployment cannot be claimed until those values come from the authenticated running AWS service.


## Fail-closed deployment evidence

After App Runner becomes reachable, `deploy.sh` fetches `/health` and writes
`evaluation/aws/deployment-evidence.json`. Evidence capture aborts unless the
running service reports the exact competition distribution/runtime pair with
`opencv5_verified: true` and its `source_sha` exactly matches the Git SHA
embedded during the container build. The evidence record also preserves the immutable ECR image identifier,
App Runner service ARN/URL, region, UTC capture time, and complete health
payload. The generated JSON is a readiness-compatible AWS evidence fragment; `cloudwatch_evidence` remains false until actual CloudWatch/App Runner telemetry has separately been captured.

This gate prevents a successful infrastructure deployment from being
misrepresented as valid competition runtime evidence when the wrong OpenCV
runtime or source revision is actually serving traffic.

## Production-container regression gate

The 2026-09-22 Docker canary reproduced an import failure (`libxcb.so.1`);
`ldd` also found missing GL and GLib libraries. The production Dockerfile now
pins the observed Python/Debian base digest, installs `libxcb1`, `libgl1`, and
`libglib2.0-0t64`, checks dependency consistency, and imports/verifies the exact
OpenCV distribution/core during the build. It does not substitute a headless
or contrib wheel for the required `opencv-python==5.0.0.93` distribution.
The service runs as UID/GID 65532. The build context uses an explicit allowlist.

CI's `container-runtime-evidence` job starts the actual production image with
no external network, a read-only root filesystem, a writable `/tmp`, dropped
capabilities, and two CPU / 2 GiB limits. `tools/container_probe.py` exercises
real loopback HTTP, checks source SHA and exact runtime, tests four QC cases,
and requires the uneven-illumination case to contain visual observations plus
`enhance_and_reanalyze` followed by acceptance. Request correlation and latency
headers must be present. A build-only success cannot satisfy this canary.

Artifacts include the probe, image metadata, service logs, Python/OS package
inventories, a 100-sample benchmark, and SHA-256 checksums. Inspect the job
conclusion as well as artifacts: failed jobs also upload troubleshooting files.
These are **container execution evidence, not authenticated AWS evidence**.
The local image ID is not an ECR registry digest. Final delivery still requires
ECR/App Runner, deployed source/runtime matching, and real CloudWatch evidence.
The pinned base plus captured inventories improve traceability; apt packages
and transitive Python dependencies are not yet a bit-for-bit build lock.

## CloudWatch/App Runner observability capture

After authenticated App Runner deployment and `deployment-evidence.json` creation, run:

```bash
./aws/capture_observability.sh evaluation/aws/deployment-evidence.json evaluation/aws/cloudwatch
```

The script generates deterministic demo traffic, resolves the AWS-documented App Runner service/application log groups from the service ARN, and captures CloudWatch events for the evidence window. `tools/aws_observability_evidence.py` fails closed unless the logs contain both source-bound OpenCV 5 QC decisions and source-bound `HAL/LabSight` Embedded Metric Format events. EMF is emitted as raw JSON on stdout so CloudWatch can parse it rather than receiving a logger-prefixed line.

The validator also rejects raw-image payload markers in captured application logs. Successful output enriches the deployment evidence with log-group names, event counts, capture timestamps, and `cloudwatch_evidence: true`. This proves telemetry from the deployed source revision; it does not infer AWS evidence from local or CI logs.

## Source-bound live endpoint evaluation

After `deployment-evidence.json` exists, run the deployed Agentic Vision suite and the frozen BBBC038-derived corpus against the same endpoint:

```bash
./aws/evaluate_deployment.sh evaluation/aws/deployment-evidence.json evaluation/aws
```

`tools/endpoint_evaluation.py` first rejects any `/health` response whose source SHA or exact `opencv-python==5.0.0.93` / `cv2.__version__==5.0.0` provenance does not match the deployment evidence. It then requires the live `/demo/judge` Agentic Vision trace to pass before sending the provenance-locked real-image corpus through `/analyze`.

Every local corpus file is SHA-256 verified before upload. The report records expected versus observed first/final actions, enhancement use, unsafe accepts, request IDs, server timing, round-trip latency, corpus-manifest digest, and source provenance. The evidence is explicitly scoped as live-endpoint evidence and does not by itself prove AWS identity.

The wrapper writes `endpoint-evaluation.json` plus `deployment-evidence-with-evaluation.json`. The latter preserves existing deployment fields and adds the source-bound deployed-evaluation readiness fragment. Feed that enriched file into `capture_observability.sh` so subsequent CloudWatch validation preserves both endpoint and observability evidence.

Final readiness now fails closed unless the evidence document proves a source-matched live judge suite, at least one scored frozen real-corpus item, and zero unsafe accepts. Local/CI/container evaluation cannot satisfy this deployed-evaluation check.
