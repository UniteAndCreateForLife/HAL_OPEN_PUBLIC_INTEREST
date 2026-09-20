from pathlib import Path

from hal_public_interest import AuditLedger, LocalRoutePolicy, RouteCandidate


def test_policy_accepts_only_explicit_local_route():
    policy = LocalRoutePolicy()
    decision = policy.choose(
        [
            RouteCandidate("cloud", "https://example.invalid", "remote", "model-a"),
            RouteCandidate("local", "http://127.0.0.1:11434", "local", "model-b"),
        ]
    )
    assert decision.allowed is True
    assert decision.route_id == "local"


def test_policy_fails_closed_without_local_route():
    decision = LocalRoutePolicy().choose(
        [RouteCandidate("cloud", "https://example.invalid", "remote", "model-a")]
    )
    assert decision.allowed is False
    assert decision.route_id is None


def test_ledger_writes_hash_linked_record(tmp_path: Path):
    ledger = AuditLedger(tmp_path / "events.jsonl")
    first = ledger.append("route_selected", {"route_id": "local"})
    second = ledger.append("work_completed", {"result": "verified"}, previous_hash=first)
    records = ledger.read()
    assert len(records) == 2
    assert records[0]["event_hash"] == first
    assert records[1]["previous_hash"] == first
    assert records[1]["event_hash"] == second
