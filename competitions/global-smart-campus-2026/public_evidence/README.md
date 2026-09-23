# Public evidence package

This directory contains judge-reviewable evidence generated from standalone
source commit `49a82066403d76da5f793b31de37720137711bde`. That commit is preserved as a
parent of the publication history and contains the exact competition source.

## Files

- `HAL_CAMPUS_EVIDENCE_DESK_DEMO.mp4`: 49.0 seconds, H.264, 1280x720.
- `recorded-demo-receipt.json`: source hashes, four observed outcomes, video
  probe, and negative competition-state claims.
- `submission-readiness.json`: exact-source readiness result with the recorded
  demo verified.
- `HAL_CAMPUS_SUBMISSION_BUNDLE_49a82066.zip`: deterministic twelve-file
  portable evidence bundle with a SHA-256 manifest.

## Integrity

- MP4 SHA-256:
  `2de1a14864c615539deffb09c904c6ce45db64e668ef60728ec4b81977c85a10`
- Demo receipt SHA-256:
  `be23b3f10ae7e452949ae237a2396f4e3f7c902516802aaf9c421745872c8a48`
- Readiness receipt SHA-256:
  `5453fd3b4493e09fca0091a8ee3c6929fdbd9d9e381b74d2ed65b9fd7c5e0fbf`
- Bundle SHA-256:
  `520e983b57cba8f538db5bfe3485c92b31be06940157e87bd1cec0920259d09f`

Verify the archive from this project directory:

```text
python build_submission_bundle.py --verify public_evidence/HAL_CAMPUS_SUBMISSION_BUNDLE_49a82066.zip
```

The package is preparation evidence only. It does not claim final application
submission, finalist selection, institutional adoption, award, or payment.
Identity, annual-turnover, representation-authority, and final form attestations
remain human-only.
