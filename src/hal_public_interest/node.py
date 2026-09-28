"""Portable HAL Node plan for a local-only Ollama-compatible endpoint.

The plan is data, not an executor: it never installs software, starts services,
loads credentials, or sends network traffic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .audit import LocalRoutePolicy, RouteCandidate


class NodePlanError(ValueError):
    pass


@dataclass(frozen=True)
class NodePlan:
    schema: str
    mode: str
    route_id: str
    endpoint: str
    models: tuple[str, ...]
    audit_ledger: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["models"] = list(self.models)
        return data


def _normalize_models(models: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in models:
        model = str(value).strip()
        if not model or model in seen:
            continue
        seen.add(model)
        out.append(model)
    if not out:
        raise NodePlanError("at least one local model is required")
    return tuple(out)


def _portable_audit_path(value: str | Path) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise NodePlanError("audit ledger path must be relative and stay inside the node root")
    text = path.as_posix().strip()
    if not text or text in {".", "/"}:
        raise NodePlanError("audit ledger path is required")
    return text


def build_node_plan(
    models: Iterable[str],
    *,
    endpoint: str = "http://127.0.0.1:11434",
    route_id: str = "ollama-local",
    audit_ledger: str | Path = "audit/node-events.jsonl",
) -> NodePlan:
    route_id = route_id.strip()
    if not route_id:
        raise NodePlanError("route_id is required")
    normalized = _normalize_models(models)
    candidate = RouteCandidate(
        route_id=route_id,
        endpoint=endpoint,
        data_residency="local",
        model=normalized[0],
    )
    decision = LocalRoutePolicy().choose([candidate])
    if not decision.allowed:
        raise NodePlanError("endpoint is not an explicit loopback HTTP route")
    return NodePlan(
        schema="hal.open_local_ai.node_plan.v1",
        mode="LOCAL_ONLY",
        route_id=route_id,
        endpoint=endpoint,
        models=normalized,
        audit_ledger=_portable_audit_path(audit_ledger),
    )
