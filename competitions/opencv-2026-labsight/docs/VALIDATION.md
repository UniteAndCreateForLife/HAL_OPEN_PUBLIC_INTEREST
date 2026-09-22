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

A networked local run on 2026-09-22 successfully downloaded all five official BBBC038 example images and froze their raw-source SHA-256 digests in `source_catalog.json`. Rebuilding the 20-item derived corpus now fails closed if any upstream source bytes drift from those locks.

That development run scored 20 derived items (10 with final-state labels): final QC agreement **1.000**, first-action agreement **0.667**, enhancement agreement **0.667**, and combined expectation agreement **0.667**. All five uneven-illumination derivatives were conservatively classified as focus recapture before the enhancement branch, so those failures remain visible rather than being relabeled. There were **0 unsafe accepts** among scored final-state samples.

The same run exposed an environment-integrity issue: installed distribution metadata reported `opencv-python==4.13.0.92` while the imported `cv2` module reported `5.0.0`. LabSight now records both values and marks that mixed environment `opencv5_verified: false`. It is development evidence only, not competition OpenCV 5 evidence.

## Exact local OpenCV 5 validation — 2026-09-22

A clean Python 3.12 virtual environment was created independently of the mixed development environment and installed directly from `requirements-competition.txt`. Package metadata reports `opencv-python==5.0.0.93`; the imported OpenCV core reports `cv2.__version__ == 5.0.0`; LabSight therefore reports `opencv5_verified: true`.

The complete deterministic suite passes **52/52 tests** in that isolated runtime. The 100-sample synthetic benchmark reports **1.000 final-decision accuracy**, **1.000 agent action/tool-call accuracy**, median latency **52.939 ms**, and P95 latency **110.717 ms**. The frozen 20-item BBBC038-derived development corpus reports final QC agreement **1.000**, first-action agreement **0.667**, enhancement agreement **0.667**, combined agreement **0.667**, and **0 unsafe accepts** among scored final-state samples.

These artifacts are genuine local OpenCV 5 execution evidence, but they are **not** Docker or authenticated AWS evidence. Final competition proof still requires the same pinned runtime in the immutable ECR/App Runner deployment.

## Focus/illumination disentanglement — 2026-09-22

The first container run preserved five genuine Agentic Vision failures: every uneven-illumination derivative was routed to focus recapture before CLAHE. Root-cause inspection showed raw Laplacian variance was confounded by smooth intensity gradients. LabSight now computes the focus score after local CLAHE contrast normalization and uses a two-level focus policy: severe blur still forces immediate recapture, while moderate focus scores permit illumination correction before the final focus gate.

On the same explicitly development-only BBBC038-derived corpus, the corrected policy reaches final QC agreement **1.000**, first-action agreement **1.000**, enhancement agreement **1.000**, and combined expectation agreement **1.000**, with **0 unsafe accepts** among scored final-state samples. This is a development-set calibration result, not held-out generalization evidence; the earlier 0.667 result remains preserved in the versioned container evidence rather than being overwritten.

The local machine used for this tuning is still a mixed OpenCV installation and therefore reports `opencv5_verified: false`. Exact-runtime confirmation must come from the pinned competition container/clean runner, and final claims still require authenticated AWS execution.

## Required final validation

Before competition submission:

1. Build the BBBC038-derived corpus and freeze its generated manifest/source hashes.
2. Build and run the competition image with OpenCV 5.x on AWS.
3. Re-run both the exact synthetic benchmark and frozen real-image corpus.
4. Record container digest, AWS service/revision, CPU/memory allocation, request concurrency, and CloudWatch/App Runner latency evidence.
5. Report per-condition and per-action failures, not only aggregate accuracy.
6. Verify the public demo endpoint or live screen-share path from a clean external client.
