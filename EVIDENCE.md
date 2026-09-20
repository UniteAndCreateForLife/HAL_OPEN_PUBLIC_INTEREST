# Evidence register

Snapshot date: 2026-09-20.

Evidence rule: every capability claim in this repository must point to an
exact source file, test, command, receipt, or an explicit `PROPOSED` /
`NEEDS HUMAN REVIEW` label. A capability in the private HAL SUPREME checkout
is not evidence that it exists in this repository.

## Verified in this draft

| Claim | Verification |
| --- | --- |
| Local route policy exists | `src/hal_public_interest/audit.py` |
| Remote-only candidates are denied | `tests/test_audit.py::test_policy_fails_closed_without_local_route` |
| Explicit loopback route is accepted | `tests/test_audit.py::test_policy_accepts_only_explicit_local_route` |
| Audit records are hash-linked | `tests/test_audit.py::test_ledger_writes_hash_linked_record` |
| Code has no declared runtime network dependency | standard-library-only implementation; must still be scanned before release |
| Package metadata is explicit | `pyproject.toml` |
| Release status is not overstated | `README.md`, `RELEASE_READINESS.md` |

## Verified about the source system

- The local checkout is `D:\HAL_SUPREME`, branch `main`, with no configured
  Git remote in the current clone.
- The GitHub repository `UniteAndCreateForLife/HAL_SUPREME` is public and its
  API response reported no license metadata at snapshot time.
- The checkout contains the named EventStore, provider, and security modules,
  but their presence is not evidence that they are suitable for public release.
- The checkout is materially dirty; the inventory deliberately does not treat
  all untracked files as reviewed or publishable.

## Private reference boundary

The following are existing private reference implementations in
`D:\HAL_SUPREME`; they are not hosted deliverables and were not copied into
this repository:

- `hal_providers/mesh.py`
- `hal_cognition/event_store.py`
- `hal_security/secret_broker.py`
- `scripts/hal_repo_intelligence.py`

Their presence can motivate future independent designs, but it does not prove
that the public-interest versions are implemented.

## Not established

- fiscal-host approval;
- charitable eligibility or legal status;
- rights clearance for every HAL asset or dependency;
- production readiness of any public repository;
- security completeness;
- correctness of the public GitHub contents beyond the API metadata read;
- permission to use any private HAL code, data, voice, avatar, or media.

## Reproduction

From this directory:

```text
python -m pytest
```

The command must be rerun in a clean environment before any external claim.

## Evidence limitations

The local source checkout has no configured Git remote and has 2,526 dirty
entries. This draft therefore cannot claim a clean source-to-public-repository
lineage yet. The public GitHub repository was checked separately through its
read-only API metadata; its contents have not been imported into this draft.
