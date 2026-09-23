# Public evidence package

This directory contains the judge-reviewable evidence generated from standalone
source commit `b5e789fcc2dbd22f80a43222b7e33ce9f8682c4f`. That commit is preserved as a
parent of the publication merge and contains the exact competition source.

## Files

- `HAL_CAMPUS_EVIDENCE_DESK_DEMO.mp4` — 49.0 seconds, H.264, 1280x720.
- `recorded-demo-receipt.json` — source hashes, four observed outcomes, video
  probe, and negative competition-state claims.
- `submission-readiness.json` — exact-source readiness result with the recorded
  demo verified.
- `HAL_CAMPUS_SUBMISSION_BUNDLE_b5e789fc.zip` — deterministic ten-file
  portable evidence bundle with a SHA-256 manifest.

## Integrity

- MP4 SHA-256:
  `2de1a14864c615539deffb09c904c6ce45db64e668ef60728ec4b81977c85a10`
- Demo receipt SHA-256:
  `c0de38cac2a5a7bca9044155338ded49690ae0fd21a37aa4d1cf3df8df8de708`
- Readiness receipt SHA-256:
  `b9498179fdfbdca33ea77347fc3fba7bf1464501ce6cc8fbd7558d9567d20525`
- Bundle SHA-256:
  `b5712e389614b51b00764a2393b22de9e22c0da57ac5e8bb73dff104afc58b9b`

Verify the archive from this project directory:

```text
python build_submission_bundle.py --verify public_evidence/HAL_CAMPUS_SUBMISSION_BUNDLE_b5e789fc.zip
```

The package is preparation evidence only. It does not claim final application
submission, finalist selection, institutional adoption, award, or payment.
Identity, annual-turnover, representation-authority, and final form attestations
remain human-only.
