import json
import logging

from labsight.observability import emit_qc_metrics


def test_emf_metrics_have_bounded_dimensions_and_no_sensitive_identifiers(caplog):
    caplog.set_level(logging.INFO, logger="labsight.metrics")
    event = emit_qc_metrics(
        decision="accept",
        source="demo:clean",
        used_enhancement=False,
        agent_steps=1,
        analysis_ms=12.3456,
    )
    assert event["Service"] == "hal-labsight"
    assert event["Decision"] == "accept"
    assert event["SourceClass"] == "demo"
    assert event["AnalysisLatency"] == 12.346
    assert event["AgentSteps"] == 1
    assert event["EnhancementUsed"] == 0
    dimensions = event["_aws"]["CloudWatchMetrics"][0]["Dimensions"]
    assert dimensions == [["Service", "Decision", "SourceClass"]]
    serialized = json.dumps(event).lower()
    for forbidden in ("request_id", "image_base64", "source_url", "sha256"):
        assert forbidden not in serialized


def test_upload_source_is_collapsed_to_bounded_source_class():
    event = emit_qc_metrics(
        decision="human_review",
        source="upload",
        used_enhancement=True,
        agent_steps=2,
        analysis_ms=1,
    )
    assert event["SourceClass"] == "upload"
    assert event["EnhancementUsed"] == 1
