# BBBC038 source-disjoint challenge v1

This is microscopy **image-quality control only**, not diagnosis or clinical validation.

## Freeze protocol

The input selection is committed **before the first policy evaluation**. It uses every
PNG image member of the official BBBC038v1 `stage1_test.zip`, sorted by member path,
without selecting on a LabSight score. The archive contains 65 source images. None
matches the raw ancestry hashes or exact decoded-pixel fingerprints of the five
recorded development sources and their 20 derivatives. Thus 65 sources remain,
producing 260 images with the existing four stressors. Exact pixel matching also
catches re-encoding and gray/RGB/RGBA layout equivalents (alpha is ignored).

The lock pins the archive, each selected member's bytes and decoded pixels, the
recorded development manifest and exclusion fingerprints, the stressor contract,
and the canonical UTF-8/LF policy/metric/transform source-file hashes. The implementation refuses
modified archive bytes, changed selection, a changed frozen policy, malformed or
oversized ZIP/PNG inputs, and output-directory replacement. ZIP contents are read
in memory; no archive paths are extracted into the filesystem. Unit tests use only
synthetic local fixtures and do not download or score this challenge.

- Source and CC0 statement: https://bbbc.broadinstitute.org/BBBC038
- Archive: https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip
- Archive bytes: 9,545,388
- Archive SHA-256: `c097954151884341448a5c77aab21f581815ad9cad203ff2ff38d6947c9f0733`
- Selection-lock SHA-256: `1d3fbb5778fcde3aeaa31c126642423f4cc4dc829ba38bf21b832adbd785c92c`
- Selection-lock hash scheme: canonical UTF-8 text with LF newlines (`utf8_lf`)
- Rights: CC0-1.0, https://creativecommons.org/publicdomain/zero/1.0/
- Attribution: BBBC038v1 contributors; Broad Institute Imaging Platform;
  Caicedo et al., Nature Methods (2019), as requested by the dataset page.

The local lock was produced using an exact-OpenCV-5 production image with networking
disabled, read-only application files, no Linux capabilities, no-new-privileges,
and a writable evidence directory. No policy metrics were computed during freeze.

## What is scored

The unchanged stressor contract gives 130 final-action expectations (65 severe-blur
and 65 clipped-exposure cases), and 195 first-action/enhancement expectations
(including 65 illumination-gradient cases). These are **scripted routing challenge
expectations**, not expert microscopy QC annotations. Native images have no invented
acceptable/unacceptable labels. Final outcomes after illumination correction remain
unscored; first-action/tool-use behavior is scored. Retain all mismatches, even when
a naturally occurring second defect could justify an alternative recapture action.

This corpus has no expected-accept final labels. A zero false-rejection count cannot
estimate specificity, and a zero unsafe-accept count cannot establish safety.
Report final-state accuracy, first-action accuracy, enhancement agreement and failure
IDs separately. Derivatives share parent images: 260 images are **not** 260 independent
sources. Exact source/pixel disjointness does not establish perceptual, acquisition,
lab, microscope, or biological independence. No such grouping metadata is claimed.
After its results are inspected, this set becomes regression evidence; do not tune
on it and call a subsequent result a fresh held-out test. Reserve new sources for
any later independent measurement.

## Reproduce using the frozen selection (Linux shell)

Run from `competitions/opencv-2026-labsight/`. Set DATA to a new evidence directory
outside the repository. Archive downloads are the only network step; generation and
scoring run offline. Use the source commit named in the first-pass receipt when
reproducing that measurement. No AWS evidence is produced by these commands.

```bash
SHA=$(git rev-parse HEAD)
DATA=/absolute/path/to/new-labsight-evidence
mkdir -p "$DATA"
curl --fail --location --proto '=https' --tlsv1.2 \
  https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip \
  --output "$DATA/stage1_test.zip"
docker build --build-arg LABSIGHT_BUILD_SHA="$SHA" -t "labsight:$SHA" .
COMMON=(--rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --cpus 2 --memory 2g \
  --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  -v "$PWD:/workspace:ro" -v "$DATA:/evidence" \
  -w /workspace -e PYTHONPATH=/workspace)
docker run "${COMMON[@]}" "labsight:$SHA" python -m tools.bbbc038_holdout build \
  --archive /evidence/stage1_test.zip \
  --lock /workspace/evaluation/real/holdout-v1/selection-lock.json \
  --output /evidence/corpus
docker run "${COMMON[@]}" "labsight:$SHA" python -m tools.bbbc038_holdout evaluate \
  --manifest /evidence/corpus/manifest.json --image-root /evidence/corpus \
  --source-sha "$SHA" --output /evidence/first-pass.json
```

`evaluate` refuses a wrong container source SHA, a non-exact OpenCV runtime, or a
policy different from the frozen files. Reports carry the manifest and selection
identities, parent source count, exact runtime, source SHA and explicit non-AWS scope.
Do not regenerate the selection lock just to bypass the frozen-policy check.

The general `freeze` subcommand is available for auditing the original selection:

```bash
python -m tools.bbbc038_holdout freeze --archive /path/stage1_test.zip \
  --development-manifest evaluation/real/generated-locked/manifest.json \
  --development-root evaluation/real/generated-locked \
  --output /new/path/selection-lock.json
```

An existing lock, manifest, or result is never overwritten by the CLI. Downloaded
images/archive and generated derivatives remain in the local evidence directory;
only locks, reports, and small verification receipts belong in Git. Independent AWS
execution and expert-reviewed QC ground truth remain separate requirements.
