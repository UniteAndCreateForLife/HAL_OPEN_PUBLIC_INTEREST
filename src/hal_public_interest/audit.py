"""Small, dependency-free primitives for a local-first AI control boundary.

This is a deliberately narrow public slice. It does not call a model, access
credentials, send network traffic, or claim to be HAL SUPREME's runtime.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit


@dataclass(frozen=True)
class RouteCandidate:
    """A route description that contains no secret material."""

    route_id: str
    endpoint: str
    data_residency: str
    model: str


@dataclass(frozen=True)
class RouteDecision:
    """The policy result for one requested route selection."""

    allowed: bool
    route_id: str | None
    reason: str


class LocalRoutePolicy:
    """Allow only explicitly local routes, preserving fail-closed behavior."""

    @staticmethod
    def _is_local(candidate: RouteCandidate) -> bool:
        if candidate.data_residency.lower() != "local":
            return False
        try:
            parsed = urlsplit(candidate.endpoint)
            if parsed.scheme != "http":
                return False
            if "@" in parsed.netloc:
                return False
            _ = parsed.port
            return parsed.hostname in ("127.0.0.1", "localhost", "::1")
        except ValueError:
            return False

    def choose(self, candidates: Iterable[RouteCandidate]) -> RouteDecision:
        for candidate in candidates:
            if self._is_local(candidate):
                return RouteDecision(True, candidate.route_id, "explicit_local_route")
        return RouteDecision(False, None, "no_explicit_local_route")


class AuditLedger:
    """Append tamper-evident, hash-linked JSONL provenance records."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, event_type: str, payload: dict, *, previous_hash: str = "") -> str:
        if not event_type or not isinstance(payload, dict):
            raise ValueError("event_type and a dictionary payload are required")
        event = {
            "schema": "hal.public_interest.audit_event.v1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        event["event_hash"] = digest
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
        return digest

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]

    def verify(self) -> int | None:
        """Verify the ledger's integrity and hash chain.

        Detects edited, inserted, deleted, and reordered records, but not
        removed trailing records. Is not a signature (whoever can rewrite
        the file can recompute every hash).
        """
        records = self.read()
        expected_prev_hash = ""
        for i, record in enumerate(records):
            if not isinstance(record, dict):
                return i
            if record.get("previous_hash") != expected_prev_hash:
                return i
            body = {k: v for k, v in record.items() if k != "event_hash"}
            canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
            recomputed_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            stored_hash = record.get("event_hash")
            if not stored_hash or stored_hash != recomputed_hash:
                return i
            expected_prev_hash = stored_hash
        return None
