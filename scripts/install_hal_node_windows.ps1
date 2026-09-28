[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$InstallOllama,
    [switch]$PullModel,
    [string]$Model = "qwen2.5:3b",
    [int]$Port = 8844,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $PSScriptRoot
$ConfigDir = Join-Path $HOME ".hal-open-local-ai"
$ConfigPath = Join-Path $ConfigDir "node.json"
$ReceiptPath = Join-Path $ConfigDir "install-receipt.json"
$OllamaInstallerUrl = "https://ollama.com/install.ps1"

function Command-Exists([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Python-Version {
    try {
        $value = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
        if ($LASTEXITCODE -ne 0) { return $null }
        return [string]$value
    } catch {
        return $null
    }
}

function Python-Supported([string]$Version) {
    if (-not $Version) { return $false }
    $parts = @($Version.Split(".") | ForEach-Object { [int]$_ })
    return $parts.Count -ge 2 -and (($parts[0] -gt 3) -or ($parts[0] -eq 3 -and $parts[1] -ge 11))
}

$pythonVersion = Python-Version
$ollamaPresent = Command-Exists "ollama"
$networkActions = @()
if (-not $ollamaPresent -and $InstallOllama) { $networkActions += "download official Ollama Windows installer script" }
if ($PullModel) { $networkActions += "ollama pull $Model" }
$plan = [ordered]@{
    schema = "hal.open_local_node.install_plan.v0"
    apply = [bool]$Apply
    root = $Root
    python = $Python
    python_version = $pythonVersion
    python_supported = (Python-Supported $pythonVersion)
    ollama_present = $ollamaPresent
    install_ollama_requested = [bool]$InstallOllama
    pull_model_requested = [bool]$PullModel
    model = $Model
    bind = "http://127.0.0.1:$Port"
    config = $ConfigPath
    network_actions = $networkActions
}

if (-not $Apply) {
    $plan | ConvertTo-Json -Depth 8
    Write-Host ""
    Write-Host "Plan only. Re-run with -Apply after review."
    Write-Host "Use -InstallOllama only to download/run Ollama's official Windows installer."
    Write-Host "Use -PullModel only to download the configured model."
    exit 0
}

if (-not (Python-Supported $pythonVersion)) { throw "Python 3.11+ is required. Observed: $pythonVersion" }
if ($Port -lt 1024 -or $Port -gt 65535) { throw "Port must be between 1024 and 65535." }

$ollamaInstallerSha256 = $null
if (-not $ollamaPresent) {
    if (-not $InstallOllama) {
        throw "Ollama is not installed. Install from https://ollama.com/download/windows or re-run with -InstallOllama."
    }
    $temporaryInstaller = Join-Path ([System.IO.Path]::GetTempPath()) ("ollama-install-" + [Guid]::NewGuid().ToString("N") + ".ps1")
    try {
        Invoke-WebRequest -Uri $OllamaInstallerUrl -OutFile $temporaryInstaller -UseBasicParsing
        $ollamaInstallerSha256 = (Get-FileHash -LiteralPath $temporaryInstaller -Algorithm SHA256).Hash
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $temporaryInstaller
        if ($LASTEXITCODE -ne 0) { throw "Ollama installer exited $LASTEXITCODE" }
    } finally {
        Remove-Item -LiteralPath $temporaryInstaller -Force -ErrorAction SilentlyContinue
    }
    $ollamaPresent = Command-Exists "ollama"
    if (-not $ollamaPresent) { throw "Ollama installed but its command is not visible in this shell. Open a new terminal and re-run." }
}

& $Python -m pip install $Root
if ($LASTEXITCODE -ne 0) { throw "Local HAL Open Local AI package install failed" }

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
& $Python -m hal_public_interest.node --config $ConfigPath init-config --model $Model --port $Port --ollama-url "http://127.0.0.1:11434" --force
if ($LASTEXITCODE -ne 0) { throw "HAL Node config creation failed" }

if ($PullModel) {
    & ollama pull $Model
    if ($LASTEXITCODE -ne 0) { throw "ollama pull failed for $Model" }
}

$ollamaVersion = $null
try { $ollamaVersion = (& ollama --version 2>&1 | Out-String).Trim() } catch {}
& $Python -m hal_public_interest.node --config $ConfigPath doctor
$doctorExit = $LASTEXITCODE

$receipt = [ordered]@{
    schema = "hal.open_local_node.install_receipt.v0"
    completed_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    root = $Root
    config = $ConfigPath
    model = $Model
    bind = "http://127.0.0.1:$Port"
    python_version = $pythonVersion
    ollama_version = $ollamaVersion
    ollama_installer_url = $(if ($InstallOllama) { $OllamaInstallerUrl } else { $null })
    ollama_installer_sha256 = $ollamaInstallerSha256
    model_pull_requested = [bool]$PullModel
    doctor_passed = ($doctorExit -eq 0)
    cloud_fallback = $false
    credentials_written = $false
    public_listener = $false
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8

if ($doctorExit -ne 0) {
    Write-Warning "Files/config installed, but local Ollama readiness did not pass. Start Ollama and run the doctor command in docs/HAL_NODE_V0.md."
    exit 2
}

Write-Host "HAL Node v0 local-only bootstrap passed."
Write-Host ("Start: hal-open-node --config " + [char]34 + $ConfigPath + [char]34 + " serve")
Write-Host ("Endpoint: http://127.0.0.1:" + $Port + "/v1/chat/completions")
