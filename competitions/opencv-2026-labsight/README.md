# HAL LabSight

**Agentic microscopy quality control for the OpenCV AI Competition 2026.**

LabSight turns microscopy image quality into a measurable perception → decision → action loop. Instead of producing a generic caption, it measures focus, illumination uniformity, clipping, edge density, segmentation occupancy, and object count with OpenCV. Those visual observations determine what happens next: accept the sample, run an illumination-correction tool and re-measure, request a focused/exposure recapture, or escalate to human review.

## Current working slice

- deterministic OpenCV microscopy metrics
- agentic two-pass analysis when illumination correction is warranted
- explicit human-review and recapture outcomes
- FastAPI service, browser demo, and CLI
- pre-decode PNG/JPEG size and dimension safety gate for public endpoint operation
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

Evidence classes are kept separate. GitHub Actions run #121 passed all four jobs
on source `9b0694299304cc46a0d5adef093543a92f9d7208`: 172 development tests and the
static readiness gate, clean exact-OpenCV-5 tests and the 100-sample benchmark,
the production-container HTTP/Agentic Vision probe, and the real browser-recording
workflow. Exact-runtime jobs verify both `opencv-python==5.0.0.93` and
`cv2.__version__==5.0.0`.

The canonical frozen BBBC038v1 source-disjoint challenge provides the strongest
real-image regression evidence:

- 65 source images, disjoint by source bytes and decoded pixels from development
- 260 controlled-stressor derivatives and 130 scored final-action cases
- 114/130 final-action agreement (87.69%)
- 168/195 first-action agreement (86.15%)
- 184/195 enhancement agreement (94.36%)
- 16 preserved final mismatches and zero unsafe accepts
- exact local OpenCV 5 production container, offline and read-only

All 16 final mismatches were blurred images conservatively routed to exposure
recapture instead of focus recapture. Eleven uneven-illumination cases did not
take the expected CLAHE first action. The challenge contains no expected-accept
final labels, and its scripted stressor expectations are not expert microscopy
ground truth; zero unsafe accepts therefore does not establish real-world safety.

The reproducible captioned judge-video draft from source `48878f5` is 62.4 seconds
and demonstrates the real four-scenario UI, two-pass CLAHE trace, judge suite,
image upload and evidence download. Later source changes mean the final video must
be regenerated from the final head and human-reviewed before submission.

These are local and CI/container results, not authenticated AWS evidence. AWS
execution is deferred by the user, and PR #1 remains draft.

## OpenCV 5 competition requirement

The final AWS image pins `opencv-python==5.0.0.93` from `requirements-competition.txt`. Verification records both the Python distribution revision (`5.0.0.93`) and the OpenCV core reported by `cv2.__version__` (`5.0.0`) so a shadowed or mixed installation cannot be mistaken for competition evidence. Final evidence must also record the immutable container digest, AWS deployment revision, benchmark output, and service logs. Local or mixed-runtime results must never be presented as OpenCV 5 competition validation.

## Agentic Vision trace

Visual evidence alters a later action. Focus is measured after local CLAHE contrast normalization so smooth shading does not masquerade as optical blur; a separate severe-blur floor still forces recapture before enhancement. Excessive illumination variation triggers `enhance_and_reanalyze`, which calls OpenCV CLAHE and performs a second QC pass. The second measurement determines acceptance, recapture, or human review. Every step is serialized into the API response.

## Responsible operation

LabSight is a quality-control assistant, not a diagnostic system. It should not be used to make clinical or biological conclusions. The public analysis endpoint accepts only PNG/JPEG, caps encoded payloads at 8 MiB, rejects dimensions above 8192 pixels or 16 megapixels before OpenCV decoding, and publishes those limits in `/health`. Real-image evaluation uses openly licensed microscopy data, documents failure cases, and preserves human review for ambiguous samples.
