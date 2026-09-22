# Real microscopy evaluation protocol

This directory holds the provenance catalog, generated manifest, and judge-facing reports for open or explicitly consented microscopy imagery.

## Current source set

The initial real-image source set is **BBBC038v1** from the Broad Bioimage Benchmark Collection. The official BBBC page describes the images as a diverse microscopy/histology nuclei collection and states that BBBC038v1 is released under **CC0**.

The checked-in `source_catalog.json` records five official BBBC038 example-image URLs, the dataset page, license identifier, license URL, citation string, and frozen raw-source SHA-256 locks. The builder fails closed if any upstream source bytes drift from those locks. The source catalog is not itself the frozen evaluation result.

## Reproducible build

Run:

```bash
PYTHONPATH=. python tools/build_bbbc038_corpus.py \
  --catalog evaluation/real/source_catalog.json \
  --output evaluation/real/generated
```

The builder downloads each official source image, records the raw-source SHA-256, then produces four deterministic QC variants:

- `native` — unscored real-image robustness baseline
- `blur` — expected focus-recapture action
- `clipped` — expected exposure-recapture action
- `uneven_illumination` — expected `enhance_and_reanalyze` first action and a second OpenCV pass

The generated `manifest.json` pins both source and derived-image hashes. This is the artifact to freeze before final AWS/OpenCV 5 scoring.

## Admission gates

Every evaluated item must have a stable HTTP(S) source URL, an explicit license, attribution, and a SHA-256 digest. Derived samples may also record a source-page URL, license URL, parent SHA-256, and deterministic derivation. `labsight.corpus` fails closed when provenance fields are malformed or image bytes do not match their recorded digest.

The manifest must declare `purpose: image_quality_control_only`. Expectations concern capture quality and agent control flow only: focus, clipping/exposure, illumination handling, recapture, acceptance, or human review. Do not add disease, diagnosis, prognosis, treatment, organism identity, or biological-outcome labels.

## Agentic evidence

The evaluator reports three independent agreement measures:

1. final QC-state agreement;
2. first-action agreement;
3. whether the expected second OpenCV enhancement pass happened.

It also reports a combined expectation score and separate failure/confusion analyses. This makes failures visible when a real source image contains a competing defect that overrides the intended stressor.

## Final evaluation

The final competition evidence must run the frozen corpus on the authenticated AWS deployment using the pinned OpenCV 5 runtime. Local OpenCV 4.x corpus runs are development evidence only.

Report successes and failures, including false recapture requests, missed stressors, and unsafe accepts. Keep native samples unscored when no defensible QC ground truth exists; they still contribute latency, trace, robustness, and provenance evidence.
