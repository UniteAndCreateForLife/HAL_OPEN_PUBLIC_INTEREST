#!/usr/bin/env bash
set -euo pipefail

DEPLOYMENT_EVIDENCE="${1:-evaluation/aws/deployment-evidence.json}"
OUTPUT_DIR="${2:-evaluation/aws/cloudwatch}"
MAX_ATTEMPTS="${LABSIGHT_CLOUDWATCH_ATTEMPTS:-12}"
SLEEP_SECONDS="${LABSIGHT_CLOUDWATCH_SLEEP_SECONDS:-5}"

for cmd in aws curl python; do
  command -v "$cmd" >/dev/null || { echo "Missing required command: $cmd" >&2; exit 2; }
done
[[ -f "$DEPLOYMENT_EVIDENCE" ]] || { echo "Missing deployment evidence: $DEPLOYMENT_EVIDENCE" >&2; exit 2; }
mkdir -p "$OUTPUT_DIR"

mapfile -t TARGETS < <(python - "$DEPLOYMENT_EVIDENCE" <<'PY'
import json
import sys
from pathlib import Path
from tools.aws_observability_evidence import app_runner_log_groups

record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
aws = record["aws"]
service_group, application_group = app_runner_log_groups(aws["service_arn"])
print(aws["region"])
print(aws["app_runner_url"])
print(service_group)
print(application_group)
PY
)
REGION="${TARGETS[0]}"
SERVICE_URL="${TARGETS[1]}"
SERVICE_GROUP="${TARGETS[2]}"
APPLICATION_GROUP="${TARGETS[3]}"

# Start the evidence window before generating deterministic judge-safe demo traffic.
START_MS="$(python - <<'PY'
import time
print(int((time.time() - 30) * 1000))
PY
)"
for scenario in clean blurred uneven clipped; do
  curl --fail --silent --show-error --retry 3 \
    "${SERVICE_URL%/}/demo/analyze/$scenario" >/dev/null
done

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  aws logs filter-log-events \
    --region "$REGION" \
    --log-group-name "$SERVICE_GROUP" \
    --start-time "$START_MS" \
    --output json >"$OUTPUT_DIR/service-logs.json"
  aws logs filter-log-events \
    --region "$REGION" \
    --log-group-name "$APPLICATION_GROUP" \
    --start-time "$START_MS" \
    --output json >"$OUTPUT_DIR/application-logs.json"

  if python tools/aws_observability_evidence.py \
      --deployment "$DEPLOYMENT_EVIDENCE" \
      --service-logs "$OUTPUT_DIR/service-logs.json" \
      --application-logs "$OUTPUT_DIR/application-logs.json" \
      --output "$OUTPUT_DIR/observability-evidence.json" >/dev/null 2>"$OUTPUT_DIR/validation-error.txt"; then
    rm -f "$OUTPUT_DIR/validation-error.txt"
    echo "CloudWatch/App Runner observability evidence captured: $OUTPUT_DIR/observability-evidence.json"
    exit 0
  fi

  if [[ "$attempt" -lt "$MAX_ATTEMPTS" ]]; then
    sleep "$SLEEP_SECONDS"
  fi
done

cat "$OUTPUT_DIR/validation-error.txt" >&2
exit 3
