# HAL LabSight

**Agentic microscopy quality control for the OpenCV AI Competition 2026.**

LabSight turns microscopy image quality into a measurable perception → decision → action loop. OpenCV measures focus, illumination uniformity, clipping, edge density, segmentation occupancy, and object count. Those observations determine the next action: accept the sample, run illumination correction and re-measure, request focus/exposure recapture, or escalate to human review.

## Current working slice

- deterministic OpenCV microscopy metrics
- agentic two-pass analysis when illumination correction is warranted
- explicit human-review and recapture outcomes
- browser demo + JSON API + CLI
- request IDs and Server-Timing headers for cloud observability
- deterministic synthetic microscopy generator and benchmark harness
- automated regression tests
- frozen local OpenCV 4.13 baseline evidence
- AWS/OpenCV 5 deployment architecture and competition report scaffolding

## Run locally

```bash
python -m pip install -e '.[test]'
pytest
labsight-evaluate --seeds 25 --output evaluation/latest
uvicorn labsight.api:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/` for the browser demo. It includes one-click clean, blurred, uneven-illumination, and clipped-exposure samples plus image upload.

Analyze a file:

```bash
labsight microscope.png
```

## Validation

The current sandbox baseline uses OpenCV 4.13.0, not OpenCV 5:

- 14/14 tests pass
- 100 synthetic benchmark samples
- 100% final-decision accuracy
- 100% agent action/tool-call accuracy
- median latency 35.109 ms
- P95 latency 71.827 ms
- `opencv5_verified: false`

See `docs/VALIDATION.md` and `evaluation/baselines/opencv-4.13-summary.json`.

## OpenCV 5 competition requirement

The final AWS image installs `opencv-python>=5,<6` from `requirements-competition.txt`. Final evidence must record the exact OpenCV 5 version, container digest, AWS deployment revision, benchmark outputs, and CloudWatch latency. Local OpenCV 4.x results must never be represented as OpenCV 5 validation.

## Agentic Vision trace

Visual evidence alters a later action. Excessive illumination variation triggers `enhance_and_reanalyze`, which calls OpenCV CLAHE and performs a second QC pass. The second measurement determines acceptance, recapture, or human review. Every step is serialized in the API response.

## Responsible operation

LabSight is image-quality control, not a diagnostic system. It does not identify disease or recommend treatment. Real-image evaluation must use consented/openly licensed microscopy data, document provenance and failure cases, and preserve human review for ambiguous samples.
