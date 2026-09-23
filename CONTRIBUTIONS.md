# Public contribution index

This page summarizes inspectable engineering contributions by
UniteAndCreateForLife. It is deliberately evidence-first: implementation,
review, submission, acceptance, award, and payment are different states.

**As of:** 2026-09-23 11:28 UTC

Verified cash received: **USD 0**

A merged PR is not payment evidence. A claim is not an award.
Unknown amounts remain unknown. The machine-readable source for this page is
[`portfolio/contributions.json`](portfolio/contributions.json), validated by
the standard-library checker in
[`src/hal_public_interest/contribution_index.py`](src/hal_public_interest/contribution_index.py).

## labsight-opencv-2026

[LabSight](https://github.com/UniteAndCreateForLife/HAL_OPEN_PUBLIC_INTEREST/pull/1)
is a non-diagnostic microscopy image-quality-control entry for the OpenCV 2026
competition. It uses OpenCV measurements to choose a later action, including a
CLAHE enhancement and second perception pass for uneven illumination.

- **State:** open draft; not finally submitted, accepted, awarded, or paid.
- **Evidence:** exact `opencv-python==5.0.0.93` / `cv2==5.0.0` container
  checks, independent frozen-corpus evaluation, an accessible browser demo,
  failure analysis, and a 64.92-second captioned presentation package.
- **Current source:** [`c87553a`](https://github.com/UniteAndCreateForLife/HAL_OPEN_PUBLIC_INTEREST/commit/c87553a66289a3fa0310e1334aff09516b524df8).
- **CI:** [run 35838447465](https://github.com/UniteAndCreateForLife/HAL_OPEN_PUBLIC_INTEREST/actions/runs/35838447465)
  passed development, exact OpenCV 5, production-container, and browser-recording jobs.
- **Funding model:** competitive prize; the competition advertises up to
  USD 12,000 across prizes, including a USD 1,000 Agentic Vision award. Those
  figures are not expected income.
- **Remaining:** human review, narration, judge-accessible hosting, and the
  separately required AWS evidence. AWS is deferred and no cloud-readiness
  claim is made.

## memanto-1852

[PR #2030](https://github.com/moorcheh-ai/memanto/pull/2030) addresses
[issue #1852](https://github.com/moorcheh-ai/memanto/issues/1852) with Vapi
call-start reliability changes and deterministic regression coverage.

- **State:** submitted and awaiting sponsor action; acceptance, award, and
  payment remain unknown.
- **Review:** the prior automated review finding is resolved; no additional
  reviewer correction is currently actionable.
- **Funding model:** competitive USD 100 bounty, not guaranteed income.
- **Claim evidence:** [existing BountyHub claim receipt](https://github.com/moorcheh-ai/memanto/issues/1852#issuecomment-5787791740).
- **Remaining:** sponsor review, acceptance decision, and any official payout
  step.

## chain-love-3925

[PR #3925](https://github.com/Chain-Love/chain-love/pull/3925) contributes
multi-network ecosystem listing updates.

- **State:** merged on September 23, 2026 after maintainer approval. The
  [merge commit](https://github.com/Chain-Love/chain-love/commit/7d2c1f2173211c7ad651ce35e10f541b6bbdddf5)
  and [maintainer receipt](https://github.com/Chain-Love/chain-love/pull/3925#issuecomment-5793217075)
  establish code acceptance.
- **Funding boundary:** the [current reward rules](https://github.com/Chain-Love/chain-love/discussions/41)
  limit paid contributions to Algorand, Filecoin, and Somnia. This PR changes
  eight different networks, so the merge is recorded as a useful portfolio
  contribution rather than verified payment-eligible work.
- **Financial state:** bounty acceptance, award, and payment remain unknown;
  verified cash received is USD 0.
- **Remaining:** no maintainer action remains for the code contribution.

## Reproduce the index check

From the repository root:

```text
python -m hal_public_interest.contribution_index portfolio/contributions.json
python -m pytest tests/test_contribution_index.py
```

The validator runs without network access. It checks the schema, contribution
IDs, status vocabulary, code-merge state, GitHub evidence links, currency
fields, and the rule that received money cannot be recorded without a known
award. Tests also require this page to carry every indexed contribution and
evidence URL.

## Scope and privacy

Only public GitHub evidence is included. The index excludes credentials,
identity documents, tax information, payout identifiers, private sponsor
messages, internal security details, and unpublished source artifacts. Financial
records use advertised, awarded, and received amounts as separate fields.
