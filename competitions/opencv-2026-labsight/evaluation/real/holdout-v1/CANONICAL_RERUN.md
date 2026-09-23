# Canonical source-disjoint rerun receipt

This rerun validates the frozen BBBC038 source-disjoint challenge after the cross-platform selection-lock hash was canonicalized. It is microscopy image-quality-control research only, not diagnosis or clinical validation.

- Source commit: `d88f18b2b16c5a1666a59614afc56be08fea83bb`
- Exact runtime: `opencv-python==5.0.0.93` / `cv2==5.0.0`
- Source images: 65
- Derived images: 260
- Scored final-action cases: 130
- Final-action agreement: 0.8769 (114/130)
- First-action agreement: 0.8615
- Enhancement agreement: 0.9436
- Unsafe accepts among scored final states: 0
- Selection-lock scheme: `utf8_lf`
- Selection-lock SHA-256: `1d3fbb5778fcde3aeaa31c126642423f4cc4dc829ba38bf21b832adbd785c92c`
- Manifest SHA-256: `088e91d67b57ca6c95e25f604611f620e21eddf4df6c747c03e391fc8affd86d`
- Full local report SHA-256: `5fb700c9a25790f71ac589542dfcd4c1994ab36e246f9da382f118c180f6697e`
- Container image ID: `sha256:1ac3304219d00f93326d050ae9a0d8aa8535474eefbc9240bc85422302fa1f9c`

The measured outcomes match the preserved first pass: 87.69% final-action agreement, 86.15% first-action agreement, 94.36% enhancement agreement, and 16 final-action mismatches. The difference is provenance: this rerun binds the frozen selection lock with the platform-independent `utf8_lf` identity `1d3fbb...`, eliminating the prior CRLF/LF ambiguity.

Execution was offline with a read-only root filesystem and workspace, dropped Linux capabilities, `no-new-privileges`, 2 CPU, and 2 GiB memory. This is local exact-runtime evidence, not AWS deployment, CloudWatch, real-world, expert-QC, diagnostic, or clinical evidence.
