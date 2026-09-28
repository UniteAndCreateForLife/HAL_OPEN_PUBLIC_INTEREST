from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_hal_node_windows.ps1"


def test_installer_defaults_to_plan_mode_and_explicit_network_switches():
    text = INSTALLER.read_text(encoding="utf-8")
    assert "[switch]$Apply" in text
    assert "[switch]$InstallOllama" in text
    assert "[switch]$PullModel" in text
    assert "if (-not $Apply)" in text
    assert "Plan only" in text


def test_installer_uses_exact_official_ollama_windows_script_without_pipe_to_iex():
    text = INSTALLER.read_text(encoding="utf-8")
    assert 'https://ollama.com/install.ps1' in text
    assert "| iex" not in text.lower()
    assert "Invoke-WebRequest -Uri $OllamaInstallerUrl" in text
    assert "Get-FileHash" in text


def test_installer_configures_only_loopback_node_endpoint():
    text = INSTALLER.read_text(encoding="utf-8")
    assert '--ollama-url "http://127.0.0.1:11434"' in text
    assert 'bind = "http://127.0.0.1:$Port"' in text
    assert "cloud_fallback = $false" in text
    assert "public_listener = $false" in text
