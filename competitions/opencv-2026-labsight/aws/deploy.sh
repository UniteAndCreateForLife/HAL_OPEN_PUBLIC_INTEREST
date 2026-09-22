#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ECR_STACK="${LABSIGHT_ECR_STACK:-hal-labsight-ecr}"
SERVICE_STACK="${LABSIGHT_SERVICE_STACK:-hal-labsight-service}"
GIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
TAG="${LABSIGHT_IMAGE_TAG:-${GIT_SHA:0:12}}"
if [[ "$TAG" == "unknown" || -z "$TAG" ]]; then TAG="$(date +%Y%m%d%H%M%S)"; fi

for cmd in aws docker; do
  command -v "$cmd" >/dev/null || { echo "Missing required command: $cmd" >&2; exit 2; }
done

aws sts get-caller-identity --region "$REGION" >/dev/null
aws cloudformation deploy --region "$REGION" --stack-name "$ECR_STACK" --template-file aws/ecr.yml

REPO_URI="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$ECR_STACK" --query 'Stacks[0].Outputs[?OutputKey==`RepositoryUri`].OutputValue' --output text)"
REGISTRY="${REPO_URI%%/*}"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build --pull --build-arg LABSIGHT_BUILD_SHA="$GIT_SHA" -t "hal-labsight:$TAG" .
docker tag "hal-labsight:$TAG" "$REPO_URI:$TAG"
docker push "$REPO_URI:$TAG"

DIGEST="$(aws ecr describe-images --region "$REGION" --repository-name hal-labsight --image-ids imageTag="$TAG" --query 'imageDetails[0].imageDigest' --output text)"
IMAGE_IDENTIFIER="$REPO_URI@$DIGEST"

aws cloudformation deploy \
  --region "$REGION" \
  --stack-name "$SERVICE_STACK" \
  --template-file aws/apprunner.yml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides ImageIdentifier="$IMAGE_IDENTIFIER"

SERVICE_URL="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$SERVICE_STACK" --query 'Stacks[0].Outputs[?OutputKey==`ServiceUrl`].OutputValue' --output text)"
SERVICE_ARN="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$SERVICE_STACK" --query 'Stacks[0].Outputs[?OutputKey==`ServiceArn`].OutputValue' --output text)"
EVIDENCE_DIR="${LABSIGHT_EVIDENCE_DIR:-evaluation/aws}"
mkdir -p "$EVIDENCE_DIR"

HEALTH_JSON="$(curl --fail --silent --show-error --retry 12 --retry-delay 5 "https://$SERVICE_URL/health")"
printf '%s' "$HEALTH_JSON" | python tools/deployment_evidence.py \
  --source-sha "$GIT_SHA" \
  --image-identifier "$IMAGE_IDENTIFIER" \
  --service-url "$SERVICE_URL" \
  --service-arn "$SERVICE_ARN" \
  --region "$REGION" \
  --output "$EVIDENCE_DIR/deployment-evidence.json" >/dev/null

cat <<OUT
HAL LabSight deployed.
Image: $IMAGE_IDENTIFIER
URL:   https://$SERVICE_URL
Health: https://$SERVICE_URL/health
Evidence: $EVIDENCE_DIR/deployment-evidence.json

The evidence file is written only after /health proves OpenCV 5 and its build_sha
matches the exact source Git SHA embedded in the immutable ECR image.
OUT
