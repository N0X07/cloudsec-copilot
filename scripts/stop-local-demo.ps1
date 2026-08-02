$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pidPath = Join-Path $projectRoot "data\generated\local-api.pid"

if (-not (Test-Path -LiteralPath $pidPath -PathType Leaf)) {
    Write-Host "No local CloudSec API PID file was found. It may already be stopped." -ForegroundColor Yellow
    exit 0
}

$apiProcessId = [int](Get-Content -LiteralPath $pidPath -Raw).Trim()
$process = Get-Process -Id $apiProcessId -ErrorAction SilentlyContinue
if (-not $process) {
    Remove-Item -LiteralPath $pidPath -Force
    Write-Host "The local CloudSec API was already stopped." -ForegroundColor Yellow
    exit 0
}

$processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$apiProcessId" -ErrorAction SilentlyContinue
if (-not $processInfo -or $processInfo.CommandLine -notmatch "uvicorn\s+app\.main:app") {
    throw "PID $apiProcessId does not look like the CloudSec local API; refusing to stop it."
}

Stop-Process -Id $apiProcessId -Force
Remove-Item -LiteralPath $pidPath -Force
Write-Host "CloudSec local API stopped (PID $apiProcessId)." -ForegroundColor Green
