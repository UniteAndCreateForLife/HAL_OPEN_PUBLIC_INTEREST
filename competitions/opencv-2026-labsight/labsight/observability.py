from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("labsight.metrics")


def emit_qc_metrics(*, decision: str, source: str, used_enhancement: bool, agent_steps: int, analysis_ms: float) -> dict[str, Any]:
    """Emit one CloudWatch Embedded Metric Format event without image content.

    Dimensions are deliberately bounded to avoid unbounded CloudWatch cardinality.
    Request IDs, image names, URLs, hashes, and payload data are never dimensions.
    """
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
        "AnalysisLatency": round(float(analysis_ms), 3),
        "AgentSteps": int(agent_steps),
        "EnhancementUsed": int(bool(used_enhancement)),
        "DecisionCount": 1,
    }
    logger.info(json.dumps(event, separators=(",", ":")))
    return event
