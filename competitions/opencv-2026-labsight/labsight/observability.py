from __future__ import annotations

import json
import os
import time
from typing import Any

import cv2


def emit_json_event(event: dict[str, Any]) -> dict[str, Any]:
    """Write one structured JSON event to stdout for App Runner/CloudWatch Logs."""
    print(json.dumps(event, separators=(",", ":")), flush=True)
    return event


def emit_qc_metrics(
    *,
    decision: str,
    source: str,
    used_enhancement: bool,
    agent_steps: int,
    analysis_ms: float,
) -> dict[str, Any]:
    """Emit source-bound CloudWatch EMF without image content or high-cardinality IDs."""
    source_class = "demo" if source.startswith("demo:") else "upload"
    event: dict[str, Any] = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": os.environ.get("LABSIGHT_METRIC_NAMESPACE", "HAL/LabSight"),
                "Dimensions": [["Service", "Decision", "SourceClass"]],
                "Metrics": [
                    {"Name": "AnalysisLatency", "Unit": "Milliseconds"},
                    {"Name": "AgentSteps", "Unit": "Count"},
                    {"Name": "EnhancementUsed", "Unit": "Count"},
                    {"Name": "DecisionCount", "Unit": "Count"},
                ],
            }],
        },
        "Service": "hal-labsight",
        "Decision": decision,
        "SourceClass": source_class,
        "build_sha": os.environ.get("LABSIGHT_BUILD_SHA", "unknown"),
        "opencv": cv2.__version__,
        "AnalysisLatency": round(float(analysis_ms), 3),
        "AgentSteps": int(agent_steps),
        "EnhancementUsed": int(bool(used_enhancement)),
        "DecisionCount": 1,
    }
    return emit_json_event(event)
