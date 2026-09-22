# Local production-container evidence, 2026-09-22

Executed source: `1cb4b6b5d502464ac42cc5c1240da8f3b9f1b4ed`.
This evidence commit follows the executed source; do not relabel its source SHA.
Docker Desktop Linux on the authorized Windows worker, limited to 2 CPUs/2 GiB.
Serving image: non-root, read-only root filesystem, no external network.

All 75 tests passed in a disposable container based on the same production
image with pytest/httpx added for testing. The live HTTP probe and corpus/
synthetic benchmarks ran in the unmodified production image.

Synthetic: 100/100 final decisions and tool-use expectations matched.
BBBC038-derived: five source images, 20 native/derived items, only 10 labeled
final decisions. Those 10 matched. First-action and enhancement agreement was
10/15; all five illumination variants requested focus recapture, not CLAHE.
No labels or thresholds were changed to conceal these failures.

The upstream native images have segmentation annotations, not expert QC labels.
These development stressors are not held-out generalization or clinical evidence.
No AWS identity, ECR digest, App Runner, or CloudWatch verification is asserted.

Versioned text copies use LF newlines. SHA256SUMS covers those repository bytes;
verify a Git archive/download rather than a checkout converted to CRLF.
Original run files are preserved in the local HAL_LABSIGHT_EVIDENCE directory.
