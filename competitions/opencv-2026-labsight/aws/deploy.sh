#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ECR_STACK="${LABSIGHT_ECR_STACK:-hal-labsight-ecr}"
SERVICE_STACK="${LABSIGHT_SERVICE_STACK:-hal-labsight-service}"
TAG="${LABSIGHT_IMAGE_TAG:-$(git rev-parse --short=12 HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"

for cmd in aws docker; do
  command -v "$cmd" >/dev/null || { echo "Missing required command: $cmd" >&2; exit 2; }
done

aws sts get-caller-identity --region "$REGION" >/dev/null
aws cloudformation deploy --region "$REGION" --stack-name "$ECR_STACK" --template-file aws/ecr.yml

REPO_URI="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$ECR_STACK" --query 'Stacks[0].Outputs[?OutputKey==`RepositoryUri`].OutputValue' --output text)"
REGISTRY="${REPO_URI%%/*}"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build --pull -t "hal-labsight:$TAG" .
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

cat <<OUT
HAL LabSight deployed.
Image: $IMAGE_IDENTIFIER
URL:   https://$SERVICE_URL
Health: https://$SERVICE_URL/health

Record the immutable image digest and /health OpenCV version in the competition evidence bundle.
OUT
