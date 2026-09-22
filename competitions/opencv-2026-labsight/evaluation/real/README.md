# Real microscopy evaluation protocol

This directory is reserved for the provenance manifest and judge-facing reports for open or explicitly consented microscopy images. Images themselves should only be committed when their license permits redistribution; otherwise the manifest records their source and immutable SHA-256 and evaluation runs against a local/downloaded copy.

## Admission gates

Every image must have: (1) a stable HTTP(S) source URL, (2) an explicit license, (3) attribution, and (4) a SHA-256 digest. `labsight.corpus` fails closed when provenance fields are absent or bytes do not match the recorded digest.

The manifest must declare `purpose: image_quality_control_only`. Labels, expectations, and reported agreement concern capture quality only: focus, exposure/clipping, illumination uniformity, structural visibility, or human-review escalation. Do not add disease, diagnosis, prognosis, treatment, organism identity, or biological-outcome labels.

## Evaluation design

Use a heterogeneous corpus spanning microscopes, magnifications, stains/modalities, image sizes, and naturally occurring quality defects where licensing permits. Freeze the manifest before final scoring. Report both successes and failures, including false recapture requests and unsafe accepts. Keep an unscored subset when no defensible QC ground truth exists; those samples still contribute trace/latency/robustness evidence but not agreement accuracy.

Final competition evidence must run the frozen corpus on the authenticated AWS deployment using the pinned OpenCV 5 runtime. Local OpenCV 4.x corpus runs are development evidence only.

## Manifest shape

```json
{
  "purpose": "image_quality_control_only",
  "items": [
    {
      "id": "stable-id",
      "path": "relative/image.png",
      "sha256": "64 lowercase hex characters",
      "source_url": "https://source.example/item",
      "license": "explicit license identifier or terms",
      "attribution": "creator/dataset citation",
      "expected_qc_status": "accept"
    }
  ]
}
```

`expected_qc_status` may be omitted when a sample is useful for robustness/provenance evidence but lacks defensible QC ground truth.
