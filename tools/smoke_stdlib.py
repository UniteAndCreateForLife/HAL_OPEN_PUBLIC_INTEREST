"""Clean-environment smoke test for the public slice; requires no pytest."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hal_public_interest import AuditLedger, LocalRoutePolicy, RouteCandidate


def main() -> None:
    decision = LocalRoutePolicy().choose(
        [RouteCandidate("cloud", "https://example.invalid", "remote", "model")]
    )
    assert decision.allowed is False
    ledger = AuditLedger(Path(__file__).with_name("smoke_events.jsonl"))
    digest = ledger.append("smoke", {"result": "pass"})
    assert len(digest) == 64
    ledger.path.unlink(missing_ok=True)
    print("stdlib smoke PASS")


if __name__ == "__main__":
    main()
