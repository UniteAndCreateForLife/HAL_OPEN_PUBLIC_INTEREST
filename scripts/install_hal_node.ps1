param(
    [string]$Model = "qwen2.5:3b",
    [string]$ConfigRoot = (Join-Path $env:LOCALAPPDATA "HALOpenLocalAI"),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$planner = Join-Path $repo "tools\plan_node.py"

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Missing prerequisite '$Name'. Install it explicitly, then rerun this installer."
    }
    return $cmd.Source
}

$python = Require-Command "python"
$ollama = Require-Command "ollama"

$target = Join-Path $ConfigRoot "node.json"
Write-Host "HAL Open Local AI node installer alpha"
Write-Host "  Python: $python"
Write-Host "  Ollama: $ollama"
Write-Host "  Model: $Model"
Write-Host "  Config: $target"
Write-Host "  Mode: LOCAL_ONLY"
Write-Host "  Endpoint: http://127.0.0.1:11434"
Write-Host ""
Write-Host "This alpha does not download packages, start services, pull models, or read credentials."

if ($DryRun) {
    Write-Host "Dry run: no files changed."
    exit 0
}

New-Item -ItemType Directory -Force -Path $ConfigRoot | Out-Null
& $python $planner --model $Model --endpoint "http://127.0.0.1:11434" --route-id "ollama-local" --audit-ledger "audit/node-events.jsonl" --output $target

if ($LASTEXITCODE -ne 0) {
    throw "Node plan generation failed with exit code $LASTEXITCODE"
}

Write-Host "Wrote local-only node plan: $target"
Write-Host "No model was pulled and no service was started."
