from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_FILES = (
    "APPLICATION_BRIEF.md",
    "README.md",
    "campus_mvp.py",
    "official_rules_snapshot.json",
    "submission_gate.py",
    "validate_package.py",
    "evidence/demo_receipt.json",
)
FORBIDDEN_PARTS = {".git", ".env", "credentials", "secrets"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(root: Path = ROOT) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_inputs(
    root: Path, demo_receipt_path: Path, readiness_receipt_path: Path
) -> dict[str, Any]:
    rules = load_json(root / "official_rules_snapshot.json")
    readiness = load_json(readiness_receipt_path)
    demo = load_json(demo_receipt_path)
    head = git_head(root)

    if demo.get("source_commit") != head:
        raise ValueError(
            f"demo source commit drift: {demo.get('source_commit')} != {head}"
        )
    video = Path(demo["video"])
    if not video.is_file():
        raise ValueError(f"demo video missing: {video}")
    if sha256(video) != demo.get("video_sha256"):
        raise ValueError("demo video SHA-256 mismatch")

    if readiness.get("status") != "PASS":
        raise ValueError("submission readiness receipt is not PASS")
    if readiness.get("source_commit") != head:
        raise ValueError("readiness source commit drift")
    recorded = readiness.get("recorded_demo", {})
    if recorded.get("verified") is not True:
        raise ValueError("readiness receipt does not verify the recorded demo")
    if recorded.get("source_commit") != head:
        raise ValueError("readiness recorded-demo source commit drift")
    if recorded.get("video_sha256") != demo.get("video_sha256"):
        raise ValueError("readiness/demo video SHA-256 mismatch")

    claims = readiness.get("claims", {})
    for name in (
        "submitted",
        "finalist",
        "awarded",
        "paid",
        "production_deployed",
        "institutional_pilot",
    ):
        if claims.get(name) is not False:
            raise ValueError("readiness receipt contains an unsupported positive claim")
    if readiness.get("deadline") != rules.get("deadline"):
        raise ValueError("deadline drift between readiness receipt and rules snapshot")
    if readiness.get("startup_prize_inr") != rules.get("startup_prize_inr"):
        raise ValueError("prize drift between readiness receipt and rules snapshot")

    for rel, expected in readiness.get("package_source_sha256", {}).items():
        path = root / rel
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"readiness package source drift: {rel}")

    return {
        "rules": rules,
        "readiness": readiness,
        "demo": demo,
        "head": head,
        "video": video,
    }


def safe_arcname(name: str) -> str:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive path: {name}")
    if {part.lower() for part in path.parts} & FORBIDDEN_PARTS:
        raise ValueError(f"forbidden archive path: {name}")
    return path.as_posix()


def write_deterministic_zip(source_dir: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for path in sorted(p for p in source_dir.rglob("*") if p.is_file()):
            arcname = safe_arcname(path.relative_to(source_dir).as_posix())
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def verify_archive(archive: Path) -> dict[str, Any]:
    with zipfile.ZipFile(archive, "r") as zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            raise ValueError("archive contains duplicate paths")
        for name in names:
            safe_arcname(name)
        manifest = json.loads(zf.read("MANIFEST.json"))
        expected = manifest["files"]
        actual_names = sorted(name for name in names if name != "MANIFEST.json")
        if actual_names != sorted(expected):
            raise ValueError("archive file set does not match manifest")
        mismatches = []
        for name, digest in expected.items():
            if hashlib.sha256(zf.read(name)).hexdigest() != digest:
                mismatches.append(name)
        if mismatches:
            raise ValueError(f"archive SHA-256 mismatch: {', '.join(mismatches)}")
        if manifest.get("claims") != {
            "submitted": False,
            "finalist": False,
            "awarded": False,
            "paid": False,
        }:
            raise ValueError(
                "archive manifest contains unsupported competition-state claims"
            )
        return {
            "status": "PASS",
            "source_commit": manifest["source_commit"],
            "file_count": len(expected),
            "archive_sha256": sha256(archive),
        }


def build_bundle(
    root: Path,
    demo_receipt_path: Path,
    readiness_receipt_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    checked = validate_inputs(root, demo_receipt_path, readiness_receipt_path)
    staging = out_dir / "bundle"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    file_hashes: dict[str, str] = {}

    for rel in DEFAULT_FILES:
        src = root / rel
        if not src.is_file():
            raise ValueError(f"required source file missing: {rel}")
        arc = safe_arcname(f"source/{rel}")
        dst = staging / Path(arc)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        file_hashes[arc] = sha256(dst)

    readiness_arc = safe_arcname("evidence/submission-readiness.json")
    readiness_dst = staging / readiness_arc
    readiness_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(readiness_receipt_path, readiness_dst)
    file_hashes[readiness_arc] = sha256(readiness_dst)

    demo_arc = safe_arcname("evidence/recorded-demo-receipt.json")
    demo_dst = staging / demo_arc
    shutil.copy2(demo_receipt_path, demo_dst)
    file_hashes[demo_arc] = sha256(demo_dst)

    video_arc = safe_arcname("media/HAL_CAMPUS_EVIDENCE_DESK_DEMO.mp4")
    video_dst = staging / video_arc
    video_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checked["video"], video_dst)
    file_hashes[video_arc] = sha256(video_dst)

    manifest = {
        "schema_version": 1,
        "competition": checked["rules"]["competition"],
        "stream": checked["rules"]["stream"],
        "source_commit": checked["head"],
        "deadline": checked["rules"]["deadline"],
        "startup_prize_inr": checked["rules"]["startup_prize_inr"],
        "scope": "portable_application_evidence_bundle_not_submission_finalist_award_or_payment",
        "human_gates": checked["rules"]["human_gates"],
        "video": {
            "path": video_arc,
            "sha256": checked["demo"]["video_sha256"],
            "probe": checked["demo"]["video_probe"],
        },
        "claims": {
            "submitted": False,
            "finalist": False,
            "awarded": False,
            "paid": False,
        },
        "files": dict(sorted(file_hashes.items())),
    }
    manifest_path = staging / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    archive = out_dir / f"HAL_CAMPUS_SUBMISSION_BUNDLE_{checked['head'][:8]}.zip"
    write_deterministic_zip(staging, archive)
    verification = verify_archive(archive)
    return {
        **verification,
        "archive": str(archive),
        "manifest_sha256": sha256(manifest_path),
        "readiness_receipt_sha256": sha256(readiness_receipt_path),
        "demo_receipt_sha256": sha256(demo_receipt_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and verify a portable Smart Campus submission-evidence bundle."
    )
    parser.add_argument("--demo-receipt", type=Path)
    parser.add_argument("--readiness-receipt", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify is None and (
        args.demo_receipt is None
        or args.readiness_receipt is None
        or args.out_dir is None
    ):
        parser.error(
            "--demo-receipt, --readiness-receipt and --out-dir are required unless --verify is used"
        )
    return args


def main() -> int:
    args = parse_args()
    if args.verify is not None:
        print(json.dumps(verify_archive(args.verify), sort_keys=True))
        return 0
    result = build_bundle(ROOT, args.demo_receipt, args.readiness_receipt, args.out_dir)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
