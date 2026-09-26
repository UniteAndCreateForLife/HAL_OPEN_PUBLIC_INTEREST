# Exact OpenCV 5 judge-suite container receipt

Source commit: `913f0042d5cd7349004cb284afa73a2a1877a82d`

Local OCI image digest: `sha256:fc412520129d30a6eee4509ba1aea0536286933fe80b3fce2aeb46fced445883`

This receipt was captured from the pinned production container on the authorized Windows Docker Desktop Linux engine. It is exact-runtime/container evidence, **not AWS deployment evidence**.

Verified runtime:
- `opencv-python==5.0.0.93`
- `cv2.__version__ == 5.0.0`
- `/health` reports `opencv5_verified: true`
- `/health` `source_sha` and `build_sha` both equal the source commit

The container was run read-only with a tmpfs, all Linux capabilities dropped, `no-new-privileges`, 2 CPUs, and a 2 GiB memory limit.

Judge suite result:
- clean: expected/observed `accept`
- blurred: expected/observed `request_recapture_focus`
- clipped: expected/observed `request_recapture_exposure`
- uneven illumination: first action `enhance_and_reanalyze`, CLAHE used, second visual pass produced, final action `accept`
- all four scenario expectations passed
- responsible-use receipt records `diagnostic_claims: false`

Files:
- `health.json` — exact runtime/source provenance
- `judge-suite.json` — expected-vs-observed actions and Agentic Vision trace
- `image-inspect.json` — local OCI image metadata and source label
- `pip-freeze.txt` — installed container packages
- `SHA256SUMS` — integrity hashes for this receipt
