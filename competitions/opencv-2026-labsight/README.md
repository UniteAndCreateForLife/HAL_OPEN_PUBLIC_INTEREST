# HAL LabSight

**Agentic microscopy quality control for the OpenCV AI Competition 2026.**

LabSight turns microscopy image quality into a measurable perception → decision → action loop. Instead of producing a generic caption, it measures focus, illumination uniformity, clipping, edge density, segmentation occupancy, and object count with OpenCV. Those visual observations determine what happens next: accept the sample, run an illumination-correction tool and re-measure, request a focused/exposure recapture, or escalate to human review.

## Current working slice

- deterministic OpenCV microscopy metrics
- agentic two-pass analysis when illumination correction is warranted
- explicit human-review and recapture outcomes
- FastAPI service, browser demo, and CLI
- deterministic synthetic microscopy benchmark
- automated tests for blur, clipping, agent tool invocation, API behavior, segmentation, and evaluation
- AWS ECR + App Runner deployment path
- competition proposal, architecture, technical-report, and validation evidence scaffolding

## Run locally

```bash
python -m pip install -e '.[test]'
pytest
labsight-evaluate --seeds 25 --output evaluation/latest
uvicorn labsight.api:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/` for the judge-facing demo.

## Current validation

The local sandbox baseline is deliberately separate from competition evidence:

- OpenCV 4.13.0
- 14/14 tests pass
- 100 benchmark samples
- 100% final-decision accuracy
- 100% agent action/tool-call accuracy
- median latency 35.109 ms
- P95 latency 71.827 ms
- `opencv5_verified: false`

## OpenCV 5 competition requirement

The final AWS image pins `opencv-python==5.0.0.93` from `requirements-competition.txt`. Final evidence must record the exact OpenCV 5 runtime, immutable container digest, AWS deployment revision, benchmark output, and service logs. Local OpenCV 4.x results must never be presented as OpenCV 5 validation.

## Agentic Vision trace

Visual evidence alters a later action. Excessive illumination variation triggers `enhance_and_reanalyze`, which calls OpenCV CLAHE and performs a second QC pass. The second measurement determines acceptance, recapture, or human review. Every step is serialized into the API response.

## Responsible operation

LabSight is a quality-control assistant, not a diagnostic system. It should not be used to make clinical or biological conclusions. Real-image evaluation will use consented/openly licensed microscopy data, document failure cases, and preserve human review for ambiguous samples.
