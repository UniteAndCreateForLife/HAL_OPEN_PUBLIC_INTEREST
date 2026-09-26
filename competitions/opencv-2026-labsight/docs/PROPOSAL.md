# Proposal: HAL LabSight

**One-line pitch:** An auditable agentic-vision service that detects microscopy capture-quality failures and uses OpenCV measurements to choose the next QC action.

## Why it matters
Bad captures waste operator time and contaminate downstream quantitative workflows. LabSight moves quality checks to the point of capture with explicit reasons and reproducible metrics.

## What makes it agentic
The system does not merely classify an image. Vision observations alter the next action. In the uneven-illumination path, the first pass invokes an OpenCV CLAHE tool and forces a second perception pass before a final accept/recapture decision.

## Technical scope
- OpenCV 5 production target
- deterministic QC metrics and segmentation
- explicit perception → decision → action trace
- web demo and JSON API
- reproducible synthetic degradation benchmark
- AWS container deployment and observability
- open/consented microscopy evaluation corpus before final judging

## Safety boundary
LabSight is image-quality control, not a diagnostic or treatment system. It does not identify disease, cell pathology, or patient conditions.
