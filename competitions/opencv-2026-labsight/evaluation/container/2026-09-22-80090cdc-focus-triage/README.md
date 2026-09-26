# Exact OpenCV 5 focus/illumination evidence

Source image build SHA: `80090cdc97a7a6b71c94cab9617f2243d52f249d`.

Scope: local Docker Desktop Linux container evidence only. This is **not** AWS deployment evidence.

The production image was rebuilt from the source SHA with `opencv-python==5.0.0.93`; `/health` reported `cv2.__version__==5.0.0`, matching `source_sha`/`build_sha`, and `opencv5_verified: true`.

The same frozen 20-item BBBC038-derived development corpus used in the earlier failure record was evaluated without relabeling. After contrast-normalized focus measurement plus a severe-blur floor, final QC agreement, first-action agreement, enhancement agreement, and combined expectation agreement are all `1.0`; unsafe accepts remain `0` among scored final-state samples.

This is development-set calibration evidence, not held-out generalization or clinical validation. The earlier `1cb4b6b5d502` container record remains preserved and shows the five original first-action/enhancement failures that motivated this change.

Artifacts:
- `http-probe.json`: live loopback HTTP / Agentic Vision canary.
- `real-corpus.json`: exact-runtime frozen-corpus evaluation.
- `image-inspect.json`: local Docker image metadata.
- `pip-freeze.txt`: Python dependency inventory from the running image.
