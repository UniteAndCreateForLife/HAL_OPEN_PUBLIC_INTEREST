from labsight.evaluation import evaluate


def test_benchmark_decisions_and_agent_actions_are_deterministic():
    summary, rows = evaluate(seeds=2)
    assert summary["samples"] == 8
    assert summary["decision_accuracy"] == 1.0
    assert summary["agent_action_accuracy"] == 1.0
    assert all(row["correct"] for row in rows)
    assert all(row["enhancement_correct"] for row in rows)


def test_benchmark_records_runtime_and_latency():
    summary, _ = evaluate(seeds=1)
    assert summary["latency_ms"]["p95"] >= 0
    assert summary["runtime"]["opencv_runtime"]
    assert summary["runtime"]["opencv_distribution"]
    assert isinstance(summary["runtime"]["opencv5_verified"], bool)
