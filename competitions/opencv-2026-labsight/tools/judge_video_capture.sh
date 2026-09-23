#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

OUTPUT="${1:-evaluation/latest/judge-recording}"
PACE="${2:-1.0}"
SOURCE_SHA="$(git rev-parse HEAD)"
IMAGE="hal-labsight:recording-${SOURCE_SHA:0:12}"
CONTAINER="labsight-recording-${SOURCE_SHA:0:12}"
PORT="${LABSIGHT_RECORDING_PORT:-18080}"
HOLDOUT="evaluation/real/holdout-v1/canonical-rerun-receipt.json"

if ! git -c core.autocrlf=input diff --quiet HEAD -- . || \
   ! git -c core.autocrlf=input diff --cached --quiet HEAD -- .; then
  echo "Refusing to record from modified tracked project files" >&2
  exit 1
fi
if [[ -n "$(git ls-files --others --exclude-standard -- .)" ]]; then
  echo "Refusing to record from untracked project files" >&2
  exit 1
fi
for command in docker python ffmpeg ffprobe; do
  command -v "$command" >/dev/null || { echo "Missing required command: $command" >&2; exit 1; }
done
[[ -f "$HOLDOUT" ]] || { echo "Missing canonical holdout receipt: $HOLDOUT" >&2; exit 1; }

cleanup() {
  docker logs "$CONTAINER" > "${OUTPUT}/service.log" 2>&1 || true
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT
mkdir -p "$OUTPUT"

docker build --progress=plain --build-arg LABSIGHT_BUILD_SHA="$SOURCE_SHA" -t "$IMAGE" . \
  2>&1 | tee "${OUTPUT}/build.log"
docker run -d --name "$CONTAINER" \
  -p "127.0.0.1:${PORT}:8080" --read-only --tmpfs /tmp \
  --cap-drop ALL --security-opt no-new-privileges --cpus 2 --memory 2g "$IMAGE" >/dev/null

python - "$PORT" <<'PY'
import json, sys, time, urllib.request
url = f"http://127.0.0.1:{sys.argv[1]}/health"
for _ in range(60):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200 and json.load(response).get("status") == "ok":
                break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("LabSight container did not become healthy")
PY

python tools/judge_video_capture.py \
  --url "http://127.0.0.1:${PORT}" \
  --output "$OUTPUT" \
  --source-sha "$SOURCE_SHA" \
  --holdout-receipt "$HOLDOUT" \
  --pace "$PACE"

cleanup
trap - EXIT
python - "$OUTPUT" <<'PY'
import sys
from pathlib import Path
from tools.judge_video_capture import write_manifest
write_manifest(Path(sys.argv[1]))
PY
