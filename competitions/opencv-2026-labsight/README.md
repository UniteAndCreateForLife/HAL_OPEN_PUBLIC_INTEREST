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

Open `http://127.0.0.1:8080/` for the judge-facing demo. `GET /demo/judge` runs the four deterministic showcase scenarios in one request and returns expected-vs-observed actions, the full uneven-illumination CLAHE trace, runtime/source provenance, and the non-diagnostic responsible-use boundary. Its `evidence_scope` explicitly states that this live runtime receipt is not AWS evidence by itself.

## Current validation

Development evidence is deliberately separated from authenticated AWS evidence. The established OpenCV 4.13 baseline remains under `evaluation/baselines/`. The current authorized-worker development suite passes **87/87 deterministic tests**; because that host Python installation is mixed, this test count is not OpenCV 5 competition-runtime evidence. Separate clean/container evidence verifies the exact `opencv-python==5.0.0.93` distribution with `cv2.__version__ == 5.0.0`:

- 100 synthetic benchmark samples
- 100% final-decision accuracy
- 100% synthetic agent action/tool-call accuracy
- local OpenCV 5 median latency 52.939 ms
- local OpenCV 5 P95 latency 110.717 ms
- 20-item provenance-locked BBBC038-derived development corpus
- current development-corpus final QC / first-action / enhancement agreement 1.000 / 1.000 / 1.000
- 0 unsafe accepts among scored real-corpus final-state samples
- local exact-runtime `opencv5_verified: true`

This is genuine local OpenCV 5 execution evidence, not Docker/App Runner competition completion.

## OpenCV 5 competition requirement

The final AWS image pins `opencv-python==5.0.0.93` from `requirements-competition.txt`. Verification records both the Python distribution revision (`5.0.0.93`) and the OpenCV core reported by `cv2.__version__` (`5.0.0`) so a shadowed or mixed installation cannot be mistaken for competition evidence. Final evidence must also record the immutable container digest, AWS deployment revision, benchmark output, and service logs. Local or mixed-runtime results must never be presented as OpenCV 5 competition validation.

## Agentic Vision trace

Visual evidence alters a later action. Focus is measured after local CLAHE contrast normalization so smooth shading does not masquerade as optical blur; a separate severe-blur floor still forces recapture before enhancement. Excessive illumination variation triggers `enhance_and_reanalyze`, which calls OpenCV CLAHE and performs a second QC pass. The second measurement determines acceptance, recapture, or human review. Every step is serialized into the API response.

## Responsible operation

LabSight is a quality-control assistant, not a diagnostic system. It should not be used to make clinical or biological conclusions. Real-image evaluation will use consented/openly licensed microscopy data, document failure cases, and preserve human review for ambiguous samples.
