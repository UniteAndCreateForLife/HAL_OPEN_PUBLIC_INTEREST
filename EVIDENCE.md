# Evidence register

Snapshot date: 2026-09-20.

Evidence rule: every capability claim in this repository must point to an
exact source file, test, command, receipt, or an explicit `PROPOSED` /
`NEEDS HUMAN REVIEW` label. A capability in the separate HAL SUPREME
checkout is not evidence that it exists in this repository.

## Verified in this public-interest repository

| Claim | Verification |
| --- | --- |
| Local route policy exists | `src/hal_public_interest/audit.py` |
| Remote-only candidates are denied | `tests/test_audit.py::test_policy_fails_closed_without_local_route` |
| Explicit loopback route is accepted | `tests/test_audit.py::test_policy_accepts_only_explicit_local_route` |
| Audit records are hash-linked | `tests/test_audit.py::test_ledger_writes_hash_linked_record` |
| Library has no declared runtime third-party dependency | standard-library implementation + `pyproject.toml` |
| Package metadata is explicit | `pyproject.toml` |
| Apache-2.0 license is published | `LICENSE`; GitHub license metadata detects Apache-2.0 |
| Repository is publicly inspectable | `https://github.com/UniteAndCreateForLife/HAL_OPEN_PUBLIC_INTEREST` |
| Scope is intentionally bounded | `README.md`, `SCOPE.md`, `RELEASE_READINESS.md` |

## Verified about the separate source system

- The reviewed local HAL SUPREME checkout was `D:\HAL_SUPREME`, branch
  `main`, and at the inventory snapshot had no configured Git remote in that
  clone.
- The GitHub repository `UniteAndCreateForLife/HAL_SUPREME` was public and
  its API response reported no license metadata at that snapshot.
- The checkout contained named EventStore, provider, security, voice, and
  production modules, but their presence is not evidence that they are
  suitable for public release.
- The source checkout was materially dirty during inventory; this repository
  therefore does not bulk-import it.

## Private reference boundary

The following were treated as separate/private reference implementations and
were not copied into this repository:

- `hal_providers/mesh.py`
- `hal_cognition/event_store.py`
- `hal_security/secret_broker.py`
- `scripts/hal_repo_intelligence.py`

Their existence can motivate independent public designs, but it does not prove
that broader public-interest versions are implemented.

## Not established

- fiscal-host approval or charitable eligibility;
- funding approval;
- rights clearance beyond the bounded repository/dependency review;
- production readiness beyond the tested minimal slice;
- security completeness or independent penetration/security review;
- permission to use any private HAL code, data, voice, avatar, identity, media,
  credential, browser state, or private integration;
- fiscal-host approval of related-party compensation or conflict controls.

## Reproduction

From the repository:

```text
python -m pytest
python tools/smoke_stdlib.py
```

The publication preparation also recorded clean-environment and scanning
results in `RELEASE_READINESS.md` and `evidence/release_audit.json`.

## Evidence limitations

HAL Open Local AI is deliberately an independent public implementation rather
than a claim of clean lineage from the broader private HAL SUPREME working
tree. Public availability and passing bounded tests do not establish legal
eligibility, fiscal-host acceptance, complete security, or production fitness.
