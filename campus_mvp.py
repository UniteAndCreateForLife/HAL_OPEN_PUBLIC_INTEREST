from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Iterable

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {"a", "an", "and", "are", "be", "campus", "for", "how", "is", "of", "should", "the", "to", "what", "where", "with"}
SENSITIVE_TERMS = {
    "medical", "diagnosis", "mental", "self-harm", "disciplinary",
    "immigration", "visa", "harassment", "assault", "accommodation denial",
}


@dataclass(frozen=True)
class PolicyDocument:
    doc_id: str
    title: str
    text: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class CampusRequest:
    request_id: str
    text: str
    channel: str = "web"

@dataclass(frozen=True)
class EvidenceHit:
    doc_id: str
    title: str
    score: float
    snippet: str


@dataclass(frozen=True)
class Decision:
    request_id: str
    disposition: str
    confidence: float
    answer: str
    evidence: tuple[EvidenceHit, ...]
    suggested_actions: tuple[str, ...]
    human_approval_required: bool
    audit_id: str


def _tokens(text: str) -> set[str]:
    return {tok for tok in TOKEN_RE.findall(text.lower()) if tok not in STOPWORDS}


def _snippet(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"

class CampusEvidenceDesk:
    def __init__(self, documents: Iterable[PolicyDocument]):
        self.documents = tuple(documents)
        if not self.documents:
            raise ValueError("at least one policy document is required")

    def _rank(self, request_text: str) -> list[EvidenceHit]:
        query = _tokens(request_text)
        hits: list[EvidenceHit] = []
        for doc in self.documents:
            body = _tokens(doc.text + " " + doc.title + " " + " ".join(doc.tags))
            overlap = len(query & body)
            union = max(1, len(query | body))
            score = overlap / union
            if score > 0:
                hits.append(EvidenceHit(doc.doc_id, doc.title, round(score, 4), _snippet(doc.text)))
        return sorted(hits, key=lambda h: (-h.score, h.doc_id))[:3]

    @staticmethod
    def _is_sensitive(text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in SENSITIVE_TERMS)

    @staticmethod
    def _action(text: str) -> str:
        lowered = text.lower()
        if any(term in lowered for term in ("wheelchair", "accessible", "accessibility")):
            return "route_accessibility_request"
        if any(term in lowered for term in ("broken", "leak", "elevator", "light", "facility", "facilities")):
            return "route_facilities_ticket"
        return "answer_with_sources"

    def analyze(self, request: CampusRequest) -> Decision:
        hits = self._rank(request.text)
        sensitive = self._is_sensitive(request.text)
        confidence = hits[0].score if hits else 0.0
        if sensitive:
            disposition = "human_review"
            answer = "This request requires a trained human reviewer; no autonomous decision was made."
            actions = ("route_human_review",)
            approval = True
        elif not hits:
            disposition = "insufficient_evidence"
            answer = "No matching policy evidence was found. Escalate rather than guess."
            actions = ("request_policy_source",)
            approval = True
        else:
            disposition = "evidence_response"
            answer = f"Relevant policy evidence: {hits[0].snippet}"
            actions = (self._action(request.text),)
            approval = actions[0] != "answer_with_sources"

        audit_material = json.dumps(
            {
                "request_id": request.request_id,
                "disposition": disposition,
                "evidence": [h.doc_id for h in hits],
                "actions": actions,
            },
            sort_keys=True,
        ).encode()
        audit_id = hashlib.sha256(audit_material).hexdigest()[:20]
        return Decision(
            request_id=request.request_id,
            disposition=disposition,
            confidence=round(confidence, 4),
            answer=answer,
            evidence=tuple(hits),
            suggested_actions=actions,
            human_approval_required=approval,
            audit_id=audit_id,
        )


def default_demo_desk() -> CampusEvidenceDesk:
    docs = (
        PolicyDocument(
            "ACCESS-001",
            "Accessibility support",
            "Students needing accessible routes or learning accommodations should contact Accessibility Services. Urgent access barriers should be routed for staff review.",
            ("accessibility", "student experience", "human review"),
        ),
        PolicyDocument(
            "FAC-002",
            "Facilities incident routing",
            "Broken elevators, lighting failures, leaks, and other facilities issues should be logged with Facilities Operations with building and room context.",
            ("facilities", "campus operations", "maintenance"),
        ),
        PolicyDocument(
            "DATA-003",
            "Privacy and data minimization",
            "Campus assistants should minimize personal data, avoid exposing student identifiers, and route sensitive cases to authorized staff with an auditable handoff.",
            ("privacy", "security", "responsible ai"),
        ),
        PolicyDocument(
            "ACADEMIC-004",
            "Academic policy evidence",
            "Academic policy answers should cite the controlling policy source and escalate when the available source is incomplete or ambiguous.",
            ("academic support", "policy", "provenance"),
        ),
    )
    return CampusEvidenceDesk(docs)


def demo_cases() -> list[CampusRequest]:
    return [
        CampusRequest("demo-1", "The science building elevator is broken. Where should this go?"),
        CampusRequest("demo-2", "What is the policy approach for academic questions?"),
        CampusRequest("demo-3", "A student disclosed a mental health concern. Decide what to do."),
        CampusRequest("demo-4", "What is the parking fine for zone Q?"),
    ]

def main() -> int:
    parser = argparse.ArgumentParser(description="HAL Campus Evidence Desk MVP")
    parser.add_argument("--demo", action="store_true", help="run deterministic sample requests")
    args = parser.parse_args()
    if not args.demo:
        parser.error("use --demo for the competition MVP demonstration")

    desk = default_demo_desk()
    payload = [asdict(desk.analyze(case)) for case in demo_cases()]
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
