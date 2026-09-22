# Submission Readiness Gate

`labsight-readiness` is the machine-readable final-submission gate for HAL LabSight. It exists to prevent development evidence from being confused with competition evidence.

## Static CI check

CI runs:

```bash
labsight-readiness --static-only --output evaluation/ci/readiness-static.json
```

This verifies that the repository contains the required build, architecture, AWS, validation, and technical-report artifacts. Static readiness does **not** mean the competition entry is ready to submit.

## Final evidence check

Final readiness requires an explicit JSON evidence document:

```bash
labsight-readiness --root . --evidence evidence/final.json --output evidence/readiness.json
```

The gate requires all of the following before returning success:

- installed `opencv-python` distribution exactly `5.0.0.93` **and** `cv2.__version__` exactly `5.0.0`; local, shadowed, or mixed installations are rejected
- immutable ECR `sha256` image digest
- HTTPS AWS App Runner endpoint
- deployed `/health` provenance matching the source Git SHA, wheel revision, and OpenCV core runtime
- CloudWatch/App Runner observability evidence
- frozen, provenance-verified non-empty microscopy corpus and an on-disk evaluation report
- documented failure cases and Agentic Vision trace evidence
- working endpoint or arranged live demonstration
- judge-accessible demo video no longer than five minutes
- explicit responsible-use attestation that LabSight is microscopy image-quality control only and makes no diagnostic claims

A blocked result is expected during development. Missing evidence must stay missing rather than being represented as complete.

## Evidence boundary

The gate is intentionally stricter than ordinary unit tests. Passing local tests under OpenCV 4.x proves development correctness only. It cannot satisfy the OpenCV 5 competition-runtime requirement. Likewise, AWS deployment checks require evidence from an authenticated deployment; configuration files alone do not count as cloud execution evidence.
