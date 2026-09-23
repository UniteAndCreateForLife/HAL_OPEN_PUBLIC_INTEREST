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

Run `python submission_gate.py` to verify that the application brief covers the official startup-stream topics, all six core submission elements, and the six published jury criteria while preserving human-only eligibility/submission boundaries.

For a source-bound application package, first create the recorded demo, then run:

```bash
python submission_gate.py --demo-receipt <artifact-directory>/recorded-demo-receipt.json --output <artifact-directory>/submission-readiness.json
```

The linked gate re-verifies the video bytes/probe, exact Git source, all four demo outcomes, package source hashes, and negative claim boundaries. Source-bound readiness receipts are generated after checkout and deliberately not committed, because committing one would immediately advance the Git source it claims to bind. This is local readiness evidence only. Organizer correspondence confirms that a pre-recorded presentation and MVP demo can serve as the official finalist presentation if selected. The gate does not submit the application, attest turnover or representation authority, establish finalist status, or imply award/payment status.

## Portable submission-evidence bundle

After the source-bound readiness gate and recorded-demo verifier pass, package the evidence without making a competition-status claim:

```bash
python build_submission_bundle.py --demo-receipt <artifact-directory>/recorded-demo-receipt.json --readiness-receipt <artifact-directory>/submission-readiness.json --out-dir <bundle-directory>
python build_submission_bundle.py --verify <bundle-directory>/HAL_CAMPUS_SUBMISSION_BUNDLE_<commit>.zip
```

The builder rejects stale source commits, altered demo media, unsupported positive competition-state claims, unsafe archive paths, and rules/readiness drift. The deterministic ZIP contains a SHA-256 manifest, current source/readiness evidence, the recorded-demo receipt, and the exact MP4. It is preparation evidence only; final application fields and eligibility/representation attestations remain human-only.
