import subprocess
from pathlib import Path

import pytest

from tools.deployment_preflight import validate_deployment_source


def _run(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "labsight").mkdir(parents=True)
    (root / ".dockerignore").write_text(
        "**\n!Dockerfile\n!labsight/\n", encoding="utf-8"
    )
    (root / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (root / "requirements-competition.txt").write_text("demo==1\n", encoding="utf-8")
    (root / "labsight" / "api.py").write_text("VALUE = 1\n", encoding="utf-8")
    _run(root, "init")
    _run(root, "config", "user.email", "tests@example.invalid")
    _run(root, "config", "user.name", "LabSight Tests")
    _run(root, "add", ".")
    _run(root, "commit", "-m", "fixture")
    return root


def test_clean_build_inputs_return_exact_head(tmp_path):
    root = _repo(tmp_path)
    assert validate_deployment_source(root) == _run(root, "rev-parse", "HEAD")


def test_tracked_build_input_change_is_rejected(tmp_path):
    root = _repo(tmp_path)
    (root / "labsight" / "api.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Docker build inputs differ"):
        validate_deployment_source(root)


def test_untracked_build_input_is_rejected(tmp_path):
    root = _repo(tmp_path)
    (root / "labsight" / "local_only.py").write_text("SECRET = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="local_only.py"):
        validate_deployment_source(root)


def test_unrelated_untracked_evidence_does_not_block(tmp_path):
    root = _repo(tmp_path)
    evidence = root / "evaluation" / "local"
    evidence.mkdir(parents=True)
    (evidence / "receipt.json").write_text("{}\n", encoding="utf-8")
    assert validate_deployment_source(root) == _run(root, "rev-parse", "HEAD")


def test_staged_build_input_change_is_rejected(tmp_path):
    root = _repo(tmp_path)
    (root / "requirements-competition.txt").write_text("demo==2\n", encoding="utf-8")
    _run(root, "add", "requirements-competition.txt")
    with pytest.raises(ValueError, match="requirements-competition.txt"):
        validate_deployment_source(root)


def test_dockerignore_change_is_rejected(tmp_path):
    root = _repo(tmp_path)
    (root / ".dockerignore").write_text(
        "**\n!Dockerfile\n!labsight/\n!local-secret.txt\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"\.dockerignore"):
        validate_deployment_source(root)
