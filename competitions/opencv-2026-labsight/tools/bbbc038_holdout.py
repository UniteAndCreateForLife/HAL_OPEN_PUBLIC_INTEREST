from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tempfile
from urllib.parse import quote
import zipfile

import cv2
import numpy as np

from labsight.corpus import evaluate_corpus, load_manifest
from labsight.real_corpus import apply_qc_stressor, write_png
from labsight.runtime import competition_runtime_info
from tools.build_bbbc038_corpus import STRESSORS

ARCHIVE_URL = "https://data.broadinstitute.org/bbbc/BBBC038/stage1_test.zip"
SOURCE_PAGE = "https://bbbc.broadinstitute.org/BBBC038"
PURPOSE = "image_quality_control_only"
POLICY_FILES = ("labsight/agent.py", "labsight/metrics.py", "labsight/real_corpus.py", "tools/build_bbbc038_corpus.py")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMBER = re.compile(r"([0-9a-f]{64})/images/\1\.png")
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_MEMBER = 8 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def pixel_digest(image: np.ndarray) -> str:
    """Exact decoded-pixel fingerprint; not perceptual or acquisition identity."""
    if image.dtype != np.uint8:
        raise ValueError("only uint8 microscopy PNGs are supported")
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    elif image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("unsupported image channel layout")
    header = json.dumps(list(image.shape), separators=(",", ":")).encode()
    return digest(header + b"\0" + np.ascontiguousarray(image).tobytes())


def decode_png(payload: bytes) -> np.ndarray:
    if len(payload) < 33 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise ValueError("invalid PNG header")
    width, height = struct.unpack(">II", payload[16:24])
    if min(width, height) < 1 or max(width, height) > 4096 or width * height > 16_000_000:
        raise ValueError("PNG dimensions exceed evaluation bounds")
    image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("OpenCV could not decode PNG")
    pixel_digest(image)
    return image


def read_archive(path: Path) -> tuple[str, list[dict]]:
    if path.stat().st_size > MAX_ARCHIVE:
        raise ValueError("archive exceeds size bound")
    archive_sha = digest(path.read_bytes())
    sources = []
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 4096 or sum(e.file_size for e in entries) > MAX_EXPANDED:
            raise ValueError("archive expansion exceeds bounds")
        names = [e.filename for e in entries]
        if len(set(names)) != len(names):
            raise ValueError("duplicate ZIP member")
        for entry in sorted(entries, key=lambda e: e.filename):
            name = entry.filename
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts or "\\" in name:
                raise ValueError("unsafe ZIP member path")
            if entry.flag_bits & 1 or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("encrypted or symlink ZIP member")
            if entry.is_dir():
                continue
            match = MEMBER.fullmatch(name)
            if not match or entry.file_size > MAX_MEMBER:
                raise ValueError("unexpected or oversized ZIP member")
            payload = archive.read(entry)
            image = decode_png(payload)
            sources.append({"id": match.group(1), "member": name, "sha256": digest(payload),
                            "pixel_sha256": pixel_digest(image), "image": image})
    if not sources:
        raise ValueError("archive contains no microscopy images")
    return archive_sha, sources


def policy_hashes() -> dict[str, str]:
    # Canonical UTF-8/LF policy text is reproducible across Windows and Linux.
    return {path: digest((PROJECT_ROOT / path).read_text(encoding="utf-8").encode("utf-8")) for path in POLICY_FILES}


def development_fingerprints(manifest: Path, root: Path) -> dict:
    raw, pixels, parents = set(), set(), set()
    for item in load_manifest(manifest):
        path = (root / item.path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("development image path escapes root")
        payload = path.read_bytes()
        if digest(payload) != item.sha256.lower():
            raise ValueError("development image SHA256 mismatch")
        if item.parent_sha256 is None:
            raise ValueError("development image requires parent provenance")
        parents.add(item.parent_sha256.lower())
        raw.update((item.sha256.lower(), item.parent_sha256.lower()))
        pixels.add(pixel_digest(decode_png(payload)))
    return {"manifest_sha256": digest(manifest.read_bytes()), "parent_sources": len(parents),
            "raw_sha256": sorted(raw), "pixel_sha256": sorted(pixels)}


def select_sources(sources: list[dict], excluded: dict) -> tuple[list[dict], list[dict]]:
    seen_raw, seen_pixels = set(excluded["raw_sha256"]), set(excluded["pixel_sha256"])
    selected, rejected = [], []
    for source in sources:
        record = {k: source[k] for k in ("id", "member", "sha256", "pixel_sha256")}
        if source["sha256"] in seen_raw or source["pixel_sha256"] in seen_pixels:
            rejected.append({**record, "reason": "exact_raw_or_decoded_pixel_overlap"})
        else:
            selected.append(record)
            seen_raw.add(source["sha256"])
            seen_pixels.add(source["pixel_sha256"])
    if not selected:
        raise ValueError("no source-disjoint images remain")
    return selected, rejected


def freeze(archive: Path, development_manifest: Path, development_root: Path) -> dict:
    """Select and seal inputs before any LabSight policy is evaluated."""
    archive_sha, sources = read_archive(archive)
    excluded = development_fingerprints(development_manifest, development_root)
    selected, rejected = select_sources(sources, excluded)
    return {"schema_version": 1, "purpose": PURPOSE, "diagnostic_claims": False,
            "dataset": "BBBC038v1", "archive_url": ARCHIVE_URL, "archive_sha256": archive_sha,
            "source_page_url": SOURCE_PAGE, "license": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "attribution": "BBBC038v1 contributors; Broad Institute Imaging Platform; Caicedo et al., Nature Methods (2019)",
            "selection": "all_image_members_lexicographic_without_policy_scoring",
            "excluded_development": excluded, "candidate_sources": len(sources),
            "sources": selected, "rejected": rejected, "policy_hash_scheme": "utf8_lf", "policy_sha256": policy_hashes(),
            "stressors": [list(s) for s in STRESSORS],
            "scope": "source_disjoint_stress_challenge_not_clinical_or_acquisition_independence"}


def build(archive: Path, lock_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("output already exists; refusing to replace frozen evidence")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("purpose") != PURPOSE or lock.get("diagnostic_claims") is not False or lock.get("schema_version") != 1:
        raise ValueError("invalid QC-only selection lock")
    if lock.get("archive_url") != ARCHIVE_URL or lock.get("license") != "CC0-1.0":
        raise ValueError("invalid source provenance")
    if lock.get("policy_hash_scheme") != "utf8_lf" or lock.get("policy_sha256") != policy_hashes() or lock.get("stressors") != [list(s) for s in STRESSORS]:
        raise ValueError("frozen policy or stressors changed; do not reuse as first-pass holdout")
    archive_sha, sources = read_archive(archive)
    if archive_sha != lock.get("archive_sha256"):
        raise ValueError("archive SHA256 mismatch")
    selected, rejected = select_sources(sources, lock["excluded_development"])
    if selected != lock.get("sources") or rejected != lock.get("rejected") or len(sources) != lock.get("candidate_sources"):
        raise ValueError("selection lock mismatch")
    by_member = {s["member"]: s for s in sources}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".labsight-holdout-", dir=output.parent) as tmp:
        stage = Path(tmp) / "corpus"
        items = []
        for source in selected:
            for stressor, final, first, enhancement in STRESSORS:
                item_id = "bbbc038-test-" + source["id"] + "__" + stressor
                path = "images/" + item_id + ".png"
                sha = write_png(stage / path, apply_qc_stressor(by_member[source["member"]]["image"], stressor))
                items.append({"id": item_id, "path": path, "sha256": sha,
                              "source_url": ARCHIVE_URL + "#" + quote(source["member"], safe="/"),
                              "source_page_url": SOURCE_PAGE, "license": lock["license"],
                              "license_url": lock["license_url"], "attribution": lock["attribution"],
                              "parent_sha256": source["sha256"], "derivation": stressor,
                              "expected_qc_status": final, "expected_first_action": first,
                              "expected_enhancement": enhancement})
        manifest = {"purpose": PURPOSE, "diagnostic_claims": False, "dataset": "BBBC038v1",
                    "split": "source_disjoint_challenge_v1", "selection_lock_sha256": digest(lock_path.read_bytes()),
                    "archive_sha256": archive_sha, "policy_hash_scheme": "utf8_lf", "policy_sha256": lock["policy_sha256"],
                    "source_count": len(selected), "excluded_source_count": len(rejected),
                    "source_locks": selected, "build_runtime": competition_runtime_info(), "items": items}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        load_manifest(stage / "manifest.json")
        stage.rename(output)
    return manifest


def evaluate(manifest: Path, root: Path, source_sha: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha) or os.environ.get("LABSIGHT_BUILD_SHA") != source_sha:
        raise ValueError("source SHA must match the executing container build")
    if competition_runtime_info()["opencv5_verified"] is not True:
        raise ValueError("exact OpenCV 5 competition runtime required")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if metadata.get("policy_hash_scheme") != "utf8_lf" or metadata.get("policy_sha256") != policy_hashes() or metadata.get("split") != "source_disjoint_challenge_v1":
        raise ValueError("frozen policy or split mismatch")
    report = evaluate_corpus(manifest, root)
    report.update({"source_sha": source_sha, "evidence_scope": "local_container_challenge_not_aws",
                   "source_count": len({i["parent_sha256"] for i in metadata["items"]}),
                   "selection_lock_sha256": metadata["selection_lock_sha256"],
                   "policy_sha256": metadata["policy_sha256"], "policy_hash_scheme": "utf8_lf", "archive_sha256": metadata["archive_sha256"],
                   "limitations": ["Controlled stressor expectations, not expert QC ground truth.",
                                   "Native images and final uneven-illumination outcomes are unscored.",
                                   "Exact source/pixel disjointness does not prove acquisition or perceptual independence.",
                                   "Derivatives share sources; image count is not independent sample count.",
                                   "After inspection, retain as regression evidence, not a fresh holdout."]})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze, build, and evaluate a source-disjoint BBBC038 QC challenge")
    parser.add_argument("action", choices=("freeze", "build", "evaluate"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--development-manifest", type=Path)
    parser.add_argument("--development-root", type=Path)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    required = {"freeze": ("archive", "development_manifest", "development_root"),
                "build": ("archive", "lock"), "evaluate": ("manifest", "image_root", "source_sha")}[args.action]
    for name in required:
        if getattr(args, name) is None:
            parser.error("missing --" + name.replace("_", "-"))
    try:
        if args.output.exists():
            raise ValueError("output already exists; refusing overwrite")
        if args.action == "freeze":
            result = freeze(args.archive, args.development_manifest, args.development_root)
        elif args.action == "build":
            result = build(args.archive, args.lock, args.output)
            print(json.dumps({"source_count": result["source_count"], "samples": len(result["items"])}))
            return 0
        else:
            result = evaluate(args.manifest, args.image_root, args.source_sha)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
        print(json.dumps({"action": args.action, "output": str(args.output), "sha256": digest(args.output.read_bytes())}))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(2, "Holdout evidence refused: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
