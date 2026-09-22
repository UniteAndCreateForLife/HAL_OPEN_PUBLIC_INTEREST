import json

from labsight.observability import emit_qc_metrics


def test_emf_metrics_are_raw_source_bound_json_without_sensitive_identifiers(capsys, monkeypatch):
    monkeypatch.setenv("LABSIGHT_BUILD_SHA", "a" * 40)
    event = emit_qc_metrics(
        decision="accept",
        source="demo:clean",
        used_enhancement=False,
        agent_steps=1,
        analysis_ms=12.3456,
    )
    stdout = capsys.readouterr().out.strip()
    assert json.loads(stdout) == event
    assert stdout.startswith("{")
    assert event["Service"] == "hal-labsight"
    assert event["Decision"] == "accept"
    assert event["SourceClass"] == "demo"
    assert event["build_sha"] == "a" * 40
    assert event["opencv"]
    assert event["AnalysisLatency"] == 12.346
    assert event["AgentSteps"] == 1
    assert event["EnhancementUsed"] == 0
    dimensions = event["_aws"]["CloudWatchMetrics"][0]["Dimensions"]
    assert dimensions == [["Service", "Decision", "SourceClass"]]
    serialized = json.dumps(event).lower()
    for forbidden in ("request_id", "image_base64", "source_url", "sha256"):
        assert forbidden not in serialized


def test_upload_source_is_collapsed_to_bounded_source_class(capsys):
    event = emit_qc_metrics(
        decision="human_review",
        source="upload",
        used_enhancement=True,
        agent_steps=2,
        analysis_ms=1,
    )
    capsys.readouterr()
    assert event["SourceClass"] == "upload"
    assert event["EnhancementUsed"] == 1
