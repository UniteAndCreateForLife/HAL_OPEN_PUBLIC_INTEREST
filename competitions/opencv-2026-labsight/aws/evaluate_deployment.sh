#!/usr/bin/env bash
set -euo pipefail

DEPLOYMENT="${1:-evaluation/aws/deployment-evidence.json}"
OUT_DIR="${2:-evaluation/aws}"
MANIFEST="${LABSIGHT_REAL_MANIFEST:-evaluation/real/generated-locked/manifest.json}"

[[ -f "$DEPLOYMENT" ]] || { echo "Missing deployment evidence: $DEPLOYMENT" >&2; exit 2; }
[[ -f "$MANIFEST" ]] || { echo "Missing frozen corpus manifest: $MANIFEST" >&2; exit 2; }

BASE_URL="$(python -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d["aws"]["app_runner_url"])' "$DEPLOYMENT")"
SOURCE_SHA="$(python -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d["source_git_sha"])' "$DEPLOYMENT")"
mkdir -p "$OUT_DIR"

python tools/endpoint_evaluation.py \
  --base-url "$BASE_URL" \
  --source-sha "$SOURCE_SHA" \
  --manifest "$MANIFEST" \
  --output "$OUT_DIR/endpoint-evaluation.json" \
  --deployment-evidence "$DEPLOYMENT" \
  --evidence-output "$OUT_DIR/deployment-evidence-with-evaluation.json"

printf 'Endpoint evaluation: %s\n' "$OUT_DIR/endpoint-evaluation.json"
printf 'Enriched deployment evidence: %s\n' "$OUT_DIR/deployment-evidence-with-evaluation.json"
