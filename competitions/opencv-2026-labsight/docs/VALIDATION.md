# Validation record

## Local sandbox baseline — OpenCV 4.13.0

This record is deliberately **not** OpenCV 5 competition evidence.

Environment observed during the run:

- Python 3.13.5
- OpenCV 4.13.0
- deterministic synthetic microscopy corpus

Commands:

```bash
pytest -q
PYTHONPATH=. python -m labsight.evaluation --seeds 25 --output evaluation/latest
```

Results:

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

## Required final validation

Before competition submission:

1. Build and run the competition image with OpenCV 5.x on AWS.
2. Re-run the exact benchmark and freeze the OpenCV 5 outputs separately.
3. Record container digest, AWS service/revision, CPU/memory allocation, request concurrency, and CloudWatch latency metrics.
4. Add a provenance-documented open/consented microscopy corpus and report per-condition failures, not only aggregate accuracy.
5. Verify the public demo endpoint or live screen-share path from a clean external client.
