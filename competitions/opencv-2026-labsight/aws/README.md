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

Final `/health` evidence must show OpenCV 5, `opencv5_verified: true`, the expected NumPy version, and the Git `build_sha`. Cloud deployment cannot be claimed until those values come from the authenticated running AWS service.
