# HAL Open Local AI

Repository working name: `HAL_OPEN_PUBLIC_INTEREST`.

This is a proposed, separate public-interest repository for small, inspectable
AI infrastructure primitives. It is intentionally not a mirror of HAL
SUPREME and it is not a release of HAL SUPREME's private, commercial, media,
credential, voice, avatar, or production systems.

The first code slice demonstrates two bounded ideas:

1. an explicit local-only route policy that fails closed when no local route is
   available; and
2. a dependency-free JSONL audit ledger with hash-linked provenance records.

It does not call an LLM, access secrets, start services, send network traffic,
publish anything, or claim parity with the HAL SUPREME runtime.

## Status

This directory was prepared locally on 2026-09-20 as a due-diligence draft and
second-pass release candidate.
It has not been pushed to GitHub, submitted to a fiscal host, or approved as a
funded project. Claims and scope remain subject to human review.

## Why this scope

The proposed public-interest work is useful independently of a commercial HAL
product: local model selection, data-locality controls, provenance, and
reproducible evaluation are general infrastructure concerns. HAL SUPREME
remains the private integration and product system. The separation is a
governance boundary, not a claim that all private code is ready for release.

## Run the minimal slice

```text
python -m pytest
```

The only runtime dependency is Python 3.11 or newer plus pytest for the test
runner. The library itself uses only the Python standard library.

## Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — narrow public architecture.
- [SCOPE.md](SCOPE.md) — included and excluded work.
- [INVENTORY.md](INVENTORY.md) — evidence-based source classification.
- [EVIDENCE.md](EVIDENCE.md) — what was actually verified.
- [GOVERNANCE.md](GOVERNANCE.md) — authority, review, and conflict controls.
- [CONFLICTS.md](CONFLICTS.md) — related-party and commercial-boundary disclosure.
- [PRIVACY.md](PRIVACY.md) — data handling and identity-document boundary.
- [SECURITY.md](SECURITY.md) — threat model and release requirements.
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution and provenance rules.
- [BUDGET.md](BUDGET.md) — six-month budget framework; compensation rate is
  intentionally unresolved pending human approval.
- [MILESTONES.md](MILESTONES.md) — proposed six-month work plan.
- [RELEASE_READINESS.md](RELEASE_READINESS.md) — second-pass audit status.
- [TIOF_RESPONSE_PACKAGE.md](TIOF_RESPONSE_PACKAGE.md) — artifact index, not
  an outbound message.

## License

The proposed code and documentation are Apache-2.0 licensed. Third-party,
private, or rights-restricted materials must not be copied into this tree.
See [LICENSE](LICENSE).
