# HAL LabSight

Agentic microscopy quality control for the OpenCV AI Competition 2026.

LabSight measures focus, illumination uniformity, clipping, edge density, segmentation occupancy, and object count with OpenCV. Those observations drive a perception-to-decision-to-action loop: accept the sample, run illumination correction and re-measure, request a focus/exposure recapture, or escalate to human review.

Current validated slice:
- deterministic OpenCV microscopy metrics
- two-pass agentic analysis for uneven illumination
- explicit recapture/human-review outcomes
- FastAPI service
- deterministic synthetic microscopy fixtures
- automated regression tests
- competition deployment target requiring OpenCV 5 on AWS

Local sandbox validation: 8/8 tests pass using OpenCV 4.13. Final competition evidence must be produced on the AWS deployment using OpenCV 5.x; local 4.13 results are not represented as OpenCV 5 validation.

Responsible-use boundary: LabSight is an image-quality control assistant, not a clinical or biological diagnostic system.
