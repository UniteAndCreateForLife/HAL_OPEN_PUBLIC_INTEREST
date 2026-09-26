import json
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


def test_policy_requires_exact_loopback_host():
    policy = LocalRoutePolicy()
    refuse_endpoints = [
        "http://127.0.0.1.evil.example",
        "http://localhost@evil.example",
        "http://localhost.evil.example:11434",
        "http://127.0.0.1:11434@evil.example",
        "http://localhost:11434.evil.example",
        "http://user@localhost:11434",
        "http://localhost.:11434",
        "http://0.0.0.0:11434",
        "http://[::1",
    ]
    for endpoint in refuse_endpoints:
        decision = policy.choose([RouteCandidate("route", endpoint, "local", "model")])
        assert decision.allowed is False
        assert decision.route_id is None

    allow_endpoints = [
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
        "http://LOCALHOST:11434",
    ]
    for endpoint in allow_endpoints:
        decision = policy.choose([RouteCandidate("route", endpoint, "local", "model")])
        assert decision.allowed is True
        assert decision.route_id == "route"

    mixed_candidates = [
        RouteCandidate("r1", "http://[::1", "local", "model"),
        RouteCandidate("r2", "http://localhost.evil.example:11434", "local", "model"),
        RouteCandidate("r3", "http://localhost:11434", "local", "model"),
    ]
    decision = policy.choose(mixed_candidates)
    assert decision.allowed is True
    assert decision.route_id == "r3"


def test_ledger_writes_hash_linked_record(tmp_path: Path):
    ledger = AuditLedger(tmp_path / "events.jsonl")
    first = ledger.append("route_selected", {"route_id": "local"})
    second = ledger.append("work_completed", {"result": "verified"}, previous_hash=first)
    records = ledger.read()
    assert len(records) == 2
    assert records[0]["event_hash"] == first
    assert records[1]["previous_hash"] == first
    assert records[1]["event_hash"] == second


def test_ledger_verify_detects_tampering(tmp_path: Path):
    assert AuditLedger(tmp_path / "missing.jsonl").verify() is None

    ledger_path = tmp_path / "events.jsonl"
    ledger = AuditLedger(ledger_path)
    first = ledger.append("route_selected", {"route_id": "local"})
    second = ledger.append("work_completed", {"result": "verified"}, previous_hash=first)
    third = ledger.append("receipt_written", {"receipt": "r-1"}, previous_hash=second)
    assert ledger.verify() is None

    lines = ledger_path.read_text(encoding="utf-8").splitlines()

    rec1 = json.loads(lines[1])
    rec1["payload"] = {"result": "tampered"}
    edited_line1 = json.dumps(rec1, sort_keys=True)
    ledger_path.write_text("\n".join([lines[0], edited_line1, lines[2]]) + "\n", encoding="utf-8")
    assert ledger.verify() == 1

    ledger_path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
    assert ledger.verify() == 1

    ledger_path.write_text("\n".join([lines[1], lines[2]]) + "\n", encoding="utf-8")
    assert ledger.verify() == 0
