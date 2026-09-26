"""Zero-spend gate: CI may only request standard hosted runners (never larger, GPU or self-hosted)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITHUB_STANDARD = {"ubuntu-latest", "ubuntu-24.04-arm", "windows-latest", "macos-latest"}
GITLAB_STANDARD = {"saas-linux-small-amd64", "saas-linux-small-arm64", "saas-windows-medium-amd64", "saas-macos-medium-m1"}


def test_github_workflows_use_only_standard_runners() -> None:
    requested = set()
    for workflow in (ROOT / ".github" / "workflows").glob("*.y*ml"):
        text = workflow.read_text(encoding="utf-8")
        requested |= set(re.findall(r"^\s*-?\s*runner:\s*([\w.-]+)\s*$", text, re.M))
        requested |= set(re.findall(r"^\s*runs-on:\s*([\w.-]+)\s*$", text, re.M))
    assert requested and requested <= GITHUB_STANDARD, requested - GITHUB_STANDARD


def test_gitlab_jobs_use_only_standard_runners() -> None:
    text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    tags = {tag.strip() for group in re.findall(r"^\s*tags:\s*\[([^\]]*)\]", text, re.M) for tag in group.split(",")}
    assert tags and tags <= GITLAB_STANDARD, tags - GITLAB_STANDARD
