# HAL Campus Evidence Desk MVP

Competition workstream: Global Smart Campus Technology Innovation Challenge 2026, startup stream.

This package is a bounded, local, non-diagnostic campus workflow prototype. It is designed to demonstrate evidence-backed routing, privacy-aware escalation, and human oversight using synthetic campus policy fixtures only.

## Run

```bash
python -m unittest -v
python campus_mvp.py --demo
python validate_package.py
```

## What the MVP proves

- Evidence-backed answers cite a policy source.
- Facilities and accessibility actions remain approval-gated proposals.
- Sensitive requests route to human review.
- Missing policy evidence causes refusal/escalation instead of guessing.
- Audit IDs are deterministic for the same request/evidence/action result.

## What it does not prove

No production deployment, institutional adoption, student-data processing, regulatory approval, revenue, paid pilot, diagnostic capability, competition submission, award, or payment is claimed.

## Recorded demo candidate

After tests pass, create a source-bound, silent H.264 demonstration outside the repository:

```bash
python record_demo.py --output-dir <artifact-directory>
python record_demo.py --verify-receipt <artifact-directory>/recorded-demo-receipt.json
```

The receipt binds the video to the exact Git commit and source hashes and fails closed on source/video drift. It is presentation evidence only, not proof of competition submission, production deployment, institutional adoption, award, or payment.

## Competition readiness gate

Run `python submission_gate.py` to verify that the application brief covers the official startup-stream topics, all six core submission elements, and the six published jury criteria while preserving human-only eligibility/submission boundaries. The gate also reruns the four deterministic MVP acceptance cases and writes `evidence/submission_readiness.json`.

This gate is local readiness evidence only. Organizer correspondence now confirms that a pre-recorded presentation and MVP demo can serve as the official finalist presentation if selected. The gate does not submit the application, attest turnover or representation authority, establish finalist status, or imply award/payment status.
