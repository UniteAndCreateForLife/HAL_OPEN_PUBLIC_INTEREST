from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
BUILD_INPUTS = (
    ".dockerignore",
    "Dockerfile",
    "requirements-competition.txt",
    "labsight",
)


def _git(project_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def validate_deployment_source(project_root: Path) -> str:
    """Return HEAD only when every Docker build input is source-clean."""
    project_root = project_root.resolve()
    for relative in BUILD_INPUTS:
        if not (project_root / relative).exists():
            raise ValueError(f"missing Docker build input: {relative}")

    source_sha = _git(project_root, "rev-parse", "HEAD").lower()
    if not _SHA40.fullmatch(source_sha):
        raise ValueError("git HEAD is not a 40-character hexadecimal SHA")

    status = _git(
        project_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *BUILD_INPUTS,
    )
    if status:
        raise ValueError(
            "refusing deployment because Docker build inputs differ from Git HEAD:\n"
            + status
        )
    return source_sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless LabSight Docker build inputs exactly match Git HEAD"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(validate_deployment_source(args.project_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
