from pathlib import Path

import pytest

from hal_public_interest.node import NodePlanError, build_node_plan


ROOT = Path(__file__).resolve().parents[1]


def test_node_plan_is_local_only_and_deduplicates_models():
    plan = build_node_plan(["qwen2.5:3b", "qwen2.5:3b", "tinyllama"])
    assert plan.mode == "LOCAL_ONLY"
    assert plan.endpoint == "http://127.0.0.1:11434"
    assert plan.models == ("qwen2.5:3b", "tinyllama")
    assert plan.audit_ledger == "audit/node-events.jsonl"


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://example.com",
        "http://192.168.1.2:11434",
        "http://127.0.0.1.evil.example:11434",
        "http://user@localhost:11434",
    ],
)
def test_node_plan_rejects_non_loopback_or_credentialed_endpoints(endpoint):
    with pytest.raises(NodePlanError):
        build_node_plan(["qwen2.5:3b"], endpoint=endpoint)


def test_node_plan_rejects_empty_models_and_escaping_audit_paths():
    with pytest.raises(NodePlanError):
        build_node_plan([])
    for path in (
        "../outside.jsonl",
        "/tmp/outside.jsonl",
        r"C:\\outside\\events.jsonl",
        r"\\\\server\\share\\events.jsonl",
        r"a\\..\\outside.jsonl",
    ):
        with pytest.raises(NodePlanError):
            build_node_plan(["qwen2.5:3b"], audit_ledger=path)


def test_portable_nested_audit_path_is_normalized():
    plan = build_node_plan(
        ["qwen2.5:3b"], audit_ledger=r"audit\\daily\\events.jsonl"
    )
    assert plan.audit_ledger == "audit/daily/events.jsonl"


def test_installer_alpha_has_no_download_package_manager_or_service_start():
    text = (ROOT / "scripts" / "install_hal_node.ps1").read_text(encoding="utf-8")
    forbidden = (
        "Invoke-WebRequest",
        "Invoke-RestMethod",
        "Start-BitsTransfer",
        "winget install",
        "choco install",
        "scoop install",
        "ollama pull",
        "Start-Service",
        "New-Service",
    )
    for token in forbidden:
        assert token.lower() not in text.lower()
    assert "[switch]$DryRun" in text
    assert "http://127.0.0.1:11434" in text
