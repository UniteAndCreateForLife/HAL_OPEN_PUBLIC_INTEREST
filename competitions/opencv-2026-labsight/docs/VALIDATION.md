# Validation record

## Local sandbox baseline — OpenCV 4.13.0

This record is deliberately **not** OpenCV 5 competition evidence.

Environment observed during the established baseline run:

- Python 3.13.5
- OpenCV 4.13.0
- deterministic synthetic microscopy corpus

Commands:

```bash
pytest -q
PYTHONPATH=. python -m labsight.evaluation --seeds 25 --output evaluation/latest
```

Established baseline results:

- Unit/API/evaluation tests: **14 passed**
- Benchmark samples: **100** (4 scenarios × 25 seeds)
- Final decision accuracy: **1.000**
- Agent action/tool-call accuracy: **1.000**
- Median latency: **35.109 ms**
- P95 latency: **71.827 ms**
- Maximum latency: **77.994 ms**
- `opencv5_verified`: **false**

The benchmark exposed and drove a real implementation improvement. Global Otsu segmentation over-segmented CLAHE-corrected fields under an illumination gradient. The implementation now uses local adaptive Gaussian thresholding, and a regression test verifies foreground occupancy remains stable after illumination correction.

The frozen baseline outputs are under `evaluation/baselines/`. These values are engineering regression evidence only and are not clinical validation.

## Real-image evidence slice — 2026-09-22

Added a provenance-first real-image path around BBBC038v1:

- official BBBC038 source-page and CC0 license metadata
- five official example-image URLs in a checked-in source catalog
- deterministic native, blur, clipping, and illumination stressors
- source and derived SHA-256 locking in the generated manifest
- evaluator scoring for final QC state, first agent action, second-pass enhancement behavior, and combined expectations
- separate failure/confusion analysis for agent actions and enhancement behavior

Focused local tests for the new transformation and agentic-scoring logic: **8 passed**.

The sandbox cannot reach the Broad image host directly, so the actual BBBC038 bytes and generated frozen manifest have **not** been fabricated or claimed here. They must be built in an environment with network access, after which the recorded hashes become the reproducibility lock.

## Required final validation

Before competition submission:

1. Build the BBBC038-derived corpus and freeze its generated manifest/source hashes.
2. Build and run the competition image with OpenCV 5.x on AWS.
3. Re-run both the exact synthetic benchmark and frozen real-image corpus.
4. Record container digest, AWS service/revision, CPU/memory allocation, request concurrency, and CloudWatch/App Runner latency evidence.
5. Report per-condition and per-action failures, not only aggregate accuracy.
6. Verify the public demo endpoint or live screen-share path from a clean external client.
