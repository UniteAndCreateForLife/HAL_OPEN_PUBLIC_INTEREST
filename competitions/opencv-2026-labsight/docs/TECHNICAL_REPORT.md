# HAL LabSight — Technical Report

## Executive summary

HAL LabSight is an auditable microscopy image-quality-control assistant. It uses
OpenCV measurements to decide whether a capture should be accepted, recaptured,
enhanced and measured again, or sent to a human. It does **not** diagnose,
prognose, treat, identify biological material, or claim clinical validation.

The distinguishing behavior is a perception → decision → action loop. Uneven
illumination can cause the policy to call an OpenCV CLAHE tool and run a second
visual pass; that new observation, rather than the original image or a language
model guess, determines the final action. Every measurement and action is
serialized for review.

The strongest completed independent-source evaluation uses 65 source images from
the CC0 BBBC038v1 `stage1_test.zip`, disjoint by source bytes and decoded pixels
from the five development sources. It produced 260 controlled-stressor images,
130 scored final-action cases, 87.69% final-action agreement, 86.15% first-action
agreement, 94.36% enhancement agreement, and zero unsafe accepts. These are
scripted routing expectations, not expert microscopy ground truth.

## Problem and intended user

Microscopy analysis can fail before downstream measurement begins. Defocus,
clipped exposure, uneven illumination, and implausible foreground occupancy can
make an image unsuitable for an automated workflow. A technician needs a fast,
inspectable answer and a concrete next action, not an opaque biological claim.

LabSight is designed for capture review and workflow routing:

- accept a capture that satisfies the configured QC policy;
- request a focus or exposure recapture;
- correct uneven illumination with CLAHE and re-measure;
- request human review when the evidence is ambiguous.

## System design

The browser and CLI submit PNG or JPEG bytes to a FastAPI service. A pre-decode
gate validates the codec, encoded size, declared dimensions, pixel count, and the
decoded shape. OpenCV then computes focus, illumination, clipping, edge,
segmentation-occupancy, and connected-object measurements. A deterministic policy
maps those values to a first action.

The important agentic branch is:

1. OpenCV observes excessive illumination variation.
2. The policy selects `enhance_and_reanalyze`.
3. The service invokes CLAHE as a named tool action.
4. OpenCV measures the corrected image again.
5. The second observation selects the final accept, recapture, or human-review
   action.

The API returns the complete trace, request ID, server timing, runtime versions,
source SHA, responsible-use declaration, and active input limits. The browser
renders the trace as measurement cards and action steps and can export an
image-free evidence JSON document.

## OpenCV implementation

LabSight uses OpenCV for the substantive perception and action stages:

- CLAHE-normalized Laplacian variance for focus assessment;
- illumination coefficient of variation;
- dark/bright clipping fractions;
- Canny-derived edge density;
- adaptive Gaussian thresholding and morphology for foreground occupancy;
- connected-components analysis for object count;
- CLAHE for the corrective tool action and the second perception pass.

Focus is measured after local contrast normalization so a smooth illumination
gradient is less likely to masquerade as optical blur. A severe-blur floor still
forces immediate recapture before enhancement. The competition runtime is pinned
to `opencv-python==5.0.0.93`, and evidence separately checks the imported
`cv2.__version__==5.0.0`; a mixed or shadowed installation does not qualify.

## Safety and responsible operation

The public analysis contract accepts only PNG and JPEG. Encoded input is limited
to 8 MiB, either axis to 8192 pixels, and the decoded image to 16 megapixels.
Declared dimensions are checked before `cv2.imdecode`, and decoded dimensions must
match the header. Invalid inputs fail closed.

LabSight never returns diagnosis, prognosis, treatment, biological identity, or
clinical interpretation. Ambiguous measurements can produce human review. Logs
and exported receipts exclude uploaded image bytes and filenames. The production
container runs as a non-root user and has been exercised locally with a read-only
root filesystem, tmpfs scratch space, all Linux capabilities dropped,
`no-new-privileges`, two CPUs, and 2 GiB memory.

## Evaluation protocol

### Deterministic synthetic regression

The synthetic benchmark generates clean, severe-blur, clipped-exposure, and
uneven-illumination captures. The current clean CI job evaluates 100 samples and
reports 1.000 final-decision and 1.000 agent action/tool-call accuracy. This
corpus verifies deterministic behavior; it is not evidence of real-image
generalization.

### Development corpus

Five openly licensed BBBC038 example sources were used during development. Their
20 deterministic derivatives exposed the original focus/illumination confound
and informed the current two-level focus policy. Results on this corpus are
development-set calibration evidence and are not reported as held-out performance.

### Frozen source-disjoint challenge

Before the first policy evaluation, the challenge selection locked every PNG in
the official BBBC038v1 `stage1_test.zip`, sorted by member path without selecting
on a LabSight score. Raw-source and decoded-pixel fingerprints exclude overlap
with the development ancestry. The frozen policy, metric implementation,
stressors, archive, members, and source hashes are all bound into the selection
receipt.

| Measure | Result |
| --- | ---: |
| Independent source images | 65 |
| Derived stressor images | 260 |
| Scored final-action cases | 130 |
| Final-action agreement | 114/130 (87.69%) |
| First-action agreement | 168/195 (86.15%) |
| Enhancement agreement | 184/195 (94.36%) |
| Exposure-recapture recall | 65/65 (100.00%) |
| Focus-recapture recall | 49/65 (75.38%) |
| CLAHE first-action recall | 54/65 (83.08%) |
| Unsafe accepts | 0 |
| Median / P95 / maximum latency | 20.764 / 133.163 / 183.667 ms |

The canonical rerun used exact `opencv-python==5.0.0.93` and `cv2==5.0.0` in an
offline, read-only local production container. It is local exact-runtime evidence,
not AWS, clinical, acquisition-independence, or expert-QC evidence.

## Failure analysis

All 16 final-action mismatches occurred on severe-blur derivatives: LabSight
requested exposure recapture instead of focus recapture. The samples therefore
still received a conservative recapture action rather than acceptance, but the
action reason was wrong. This indicates that strong brightness/clipping evidence
can outrank the intended blur label on naturally heterogeneous source images.

The first-action analysis adds 11 uneven-illumination misses. Ten were routed to
focus recapture and one to human review instead of invoking CLAHE. Consequently,
54 of 65 uneven cases executed the expected enhancement. None of the missed cases
was silently accepted.

The challenge contains no expected-accept final labels. Therefore zero unsafe
accepts cannot estimate specificity or real-world safety, and the recorded zero
false rejections is not meaningful. The 260 derivatives also represent 65 parent
sources, not 260 independent samples. Exact byte/pixel disjointness does not prove
independence by laboratory, microscope, acquisition protocol, or biological
content. After inspection, this challenge is regression evidence; future
independent measurement must reserve new sources and ideally expert QC labels.

## Demonstration and accessibility

The responsive browser demo supports keyboard operation, readable measurement
cards, visible busy/error states, recovery from controlled failures, and an
image-free evidence download. `GET /demo/judge` runs the four showcase scenarios
and verifies expected versus observed actions.

A reproducible source-bound recording workflow produces WebM, H.264 MP4, WebVTT
captions, screenshots, observed JSON receipts, logs, media metadata, and a SHA-256
manifest. The inspected draft recorded from source `48878f5` is 62.4 seconds at
1280×720 and shows the real container-backed workflow. Because later commits have
changed the source, a final judge video must be regenerated from the final head,
human-reviewed, narrated or otherwise editorially approved, and hosted at a
judge-accessible URL.

## Reproducibility

From `competitions/opencv-2026-labsight/`:

```bash
python -m pip install -e '.[test]'
pytest -q
labsight-readiness --static-only
labsight-evaluate --seeds 25 --output evaluation/latest
uvicorn labsight.api:app --host 127.0.0.1 --port 8080
```

The exact competition dependency set is in `requirements-competition.txt`. The
source-disjoint challenge protocol and immutable identities are documented in
`evaluation/real/holdout-v1/README.md`; the canonical compact receipt is
`evaluation/real/holdout-v1/canonical-rerun-receipt.json`.

## Deployment design and current evidence boundary

The preserved cloud design builds a source-bound production image, pushes it to
an immutable Amazon ECR digest, deploys that digest to AWS App Runner, verifies
`/health`, evaluates the deployed endpoint, and captures CloudWatch/App Runner
observability. That architecture remains a competition requirement.

AWS authentication and deployment are currently **deferred by the user**. No ECR
digest, App Runner endpoint, CloudWatch/X-Ray telemetry, or deployed benchmark is
claimed. Local, CI, and container results do not substitute for AWS evidence.
PR #1 therefore remains draft, and the final Devpost submission, eligibility,
tax, and attestation steps remain human/account actions.

## Evidence identities

- Challenge source commit: `d88f18b2b16c5a1666a59614afc56be08fea83bb`
- Selection-lock SHA-256: `1d3fbb5778fcde3aeaa31c126642423f4cc4dc829ba38bf21b832adbd785c92c`
- Challenge manifest SHA-256: `088e91d67b57ca6c95e25f604611f620e21eddf4df6c747c03e391fc8affd86d`
- Full challenge report SHA-256: `5fb700c9a25790f71ac589542dfcd4c1994ab36e246f9da382f118c180f6697e`
- Inspected draft MP4 SHA-256: `2dc94715db88afc13b3d750075c29090ff3e8f807740ea518330b5481f706af2`

These identities make the evidence auditable without placing the licensed source
archive, generated image corpus, uploaded user images, or private account data in
the public repository.
