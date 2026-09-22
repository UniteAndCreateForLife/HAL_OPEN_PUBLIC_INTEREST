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
