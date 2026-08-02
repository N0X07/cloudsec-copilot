[CmdletBinding()]
param(
    [switch]$Reset,
    [switch]$Approve,
    [switch]$IncludeAgent,
    [switch]$OpenDocs,
    [switch]$Local,
    [string]$BaseUri = "http://localhost:8000"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$positiveEventId = "00000000-0000-4000-8000-000000000011"
$negativeEventId = "00000000-0000-4000-8000-000000000012"

function Write-Section {
    param([Parameter(Mandatory)][string]$Title)

    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Invoke-DockerCommand {
    param([Parameter(Mandatory)][string[]]$DockerArguments)

    & docker @DockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($DockerArguments -join ' ')"
    }
}

function Wait-CloudSecApi {
    param([Parameter(Mandatory)][string]$HealthUri)

    foreach ($attempt in 1..45) {
        try {
            $health = Invoke-RestMethod -Method Get -Uri $HealthUri -TimeoutSec 2
            if ($health.status -eq "ok") {
                return $health
            }
        }
        catch {
            if ($attempt -eq 45) {
                throw "CloudSec Copilot did not become healthy within 90 seconds."
            }
        }
        Start-Sleep -Seconds 2
    }

    throw "CloudSec Copilot health endpoint did not return status=ok."
}

function Import-EventFile {
    param([Parameter(Mandatory)][string]$Path)

    $resolvedPath = (Resolve-Path -LiteralPath $Path).Path
    Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUri/api/v1/events/import" `
        -ContentType "application/json" `
        -InFile $resolvedPath
}

function Write-JsonResult {
    param([Parameter(Mandatory)]$Value)

    $Value | ConvertTo-Json -Depth 10
}

if (-not $Local -and -not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found. Install and start Docker Desktop before running the demo."
}

if ($IncludeAgent -and [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    throw "-IncludeAgent requires OPENAI_API_KEY in the current PowerShell session."
}

$localApiProcess = $null
$localPidPath = Join-Path $projectRoot "data\generated\local-api.pid"
$demoSucceeded = $false

Push-Location $projectRoot
try {
    if ($Local) {
        Write-Section "Start local API with SQLite (no Docker download required)"
        $localPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
        $localDatabase = Join-Path $projectRoot "cloudsec-local-demo.db"
        $generatedDirectory = Split-Path -Parent $localPidPath
        $stdoutLog = Join-Path $generatedDirectory "local-api.stdout.log"
        $stderrLog = Join-Path $generatedDirectory "local-api.stderr.log"

        if (-not (Test-Path -LiteralPath $localPython -PathType Leaf)) {
            throw "Local Python environment was not found: $localPython"
        }
        New-Item -ItemType Directory -Path $generatedDirectory -Force | Out-Null

        $existingHealth = $null
        try {
            $existingHealth = Invoke-RestMethod -Method Get -Uri "$BaseUri/health" -TimeoutSec 2
        }
        catch {
            $existingHealth = $null
        }

        if ($existingHealth -and $existingHealth.status -eq "ok") {
            if ($Reset) {
                throw "A CloudSec API is already using $BaseUri. Run stop-local-demo.cmd before using -Reset."
            }
            Write-Host "Reusing the healthy CloudSec API at $BaseUri."
        }
        else {
            if ($Reset -and (Test-Path -LiteralPath $localDatabase -PathType Leaf)) {
                Write-Host "Removing only the local SQLite demo database..." -ForegroundColor Yellow
                Remove-Item -LiteralPath $localDatabase -Force
            }

            $previousDatabaseUrl = $env:DATABASE_URL
            $previousAppEnv = $env:APP_ENV
            try {
                $env:DATABASE_URL = "sqlite:///./cloudsec-local-demo.db"
                $env:APP_ENV = "development"

                # Some Windows sandbox/launcher environments provide both
                # `Path` and `PATH`. Start-Process treats those as duplicate
                # case-insensitive keys, so normalize them before launching
                # the local API child process.
                $pathKeys = @(
                    [System.Environment]::GetEnvironmentVariables().Keys |
                        Where-Object { $_.ToString().ToLowerInvariant() -eq "path" }
                )
                if ($pathKeys.Count -gt 1) {
                    $processPath = [System.Environment]::GetEnvironmentVariable(
                        "Path",
                        [System.EnvironmentVariableTarget]::Process
                    )
                    [System.Environment]::SetEnvironmentVariable(
                        "PATH",
                        $null,
                        [System.EnvironmentVariableTarget]::Process
                    )
                    [System.Environment]::SetEnvironmentVariable(
                        "Path",
                        $processPath,
                        [System.EnvironmentVariableTarget]::Process
                    )
                }

                $localApiProcess = Start-Process `
                    -FilePath $localPython `
                    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
                    -WorkingDirectory $projectRoot `
                    -RedirectStandardOutput $stdoutLog `
                    -RedirectStandardError $stderrLog `
                    -WindowStyle Hidden `
                    -PassThru
            }
            finally {
                $env:DATABASE_URL = $previousDatabaseUrl
                $env:APP_ENV = $previousAppEnv
            }
            Set-Content -LiteralPath $localPidPath -Value $localApiProcess.Id -Encoding ASCII
            Write-Host "Local API process: $($localApiProcess.Id)"
        }
    }
    else {
        Write-Section "Start local services with Docker Compose"
        if ($Reset) {
            Write-Host "Removing only the local Docker demo database volume..." -ForegroundColor Yellow
            Invoke-DockerCommand -DockerArguments @("compose", "down", "--volumes")
        }

        Invoke-DockerCommand -DockerArguments @("compose", "up", "--build", "--detach")
    }

    $health = Wait-CloudSecApi -HealthUri "$BaseUri/health"
    Write-JsonResult $health

    Write-Section "Import labeled CloudTrail-style events"
    $firstImport = Import-EventFile -Path "data/cloudtrail_events.json"
    $secondImport = Import-EventFile -Path "data/additional_security_events.json"
    Write-JsonResult ([ordered]@{
        first_dataset = $firstImport
        second_dataset = $secondImport
    })

    Write-Section "Compare suspicious and benign events"
    $positive = Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUri/api/v1/events/$positiveEventId/analyze-all"
    $negative = Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUri/api/v1/events/$negativeEventId/analyze-all"

    if ($positive.matched_rules -lt 1 -or $positive.findings[0].rule_id -ne "AWS-LOG-001") {
        throw "The known-positive CloudTrail StopLogging event did not match AWS-LOG-001."
    }
    if ($negative.matched_rules -ne 0) {
        throw "The known-benign CloudTrail StartLogging event unexpectedly matched a rule."
    }

    Write-JsonResult ([ordered]@{
        suspicious_stop_logging = $positive
        benign_start_logging = $negative
    })

    $incidentId = $positive.findings[0].incident_id

    Write-Section "Build evidence-backed incident report"
    $report = Invoke-RestMethod `
        -Method Get `
        -Uri "$BaseUri/api/v1/incidents/$incidentId/report"
    Write-JsonResult $report

    if ($IncludeAgent) {
        Write-Section "Run bounded AI analyst"
        $agentResult = Invoke-RestMethod `
            -Method Post `
            -Uri "$BaseUri/api/v1/incidents/$incidentId/agent-analysis"
        Write-JsonResult $agentResult
    }

    if ($Approve) {
        Write-Section "Record human approval without executing remediation"
        if ($report.remediation_state -eq "awaiting_human_approval") {
            $approvalBody = @{
                decision = "approve"
                decided_by = "local-demo-reviewer"
                rationale = "Evidence reviewed; authorize simulated recovery only."
            } | ConvertTo-Json

            $approval = Invoke-RestMethod `
                -Method Post `
                -Uri "$BaseUri/api/v1/incidents/$incidentId/approval" `
                -ContentType "application/json" `
                -Body $approvalBody
            Write-JsonResult $approval
        }
        else {
            Write-Host "This incident already has a decision; reusing its existing audit history."
        }
    }

    Write-Section "Verify final report and audit trail"
    $finalReport = Invoke-RestMethod `
        -Method Get `
        -Uri "$BaseUri/api/v1/incidents/$incidentId/report"
    $audit = Invoke-RestMethod `
        -Method Get `
        -Uri "$BaseUri/api/v1/incidents/$incidentId/audit"

    Write-JsonResult ([ordered]@{
        report = $finalReport
        audit = $audit
    })

    if ($Approve -and $finalReport.remediation_state -ne "approved_not_executed") {
        throw "Approval was recorded, but the safe approved_not_executed state was not observed."
    }

    Write-Section "Demo complete"
    Write-Host "Suspicious event: $positiveEventId -> AWS-LOG-001" -ForegroundColor Green
    Write-Host "Benign event:     $negativeEventId -> no finding" -ForegroundColor Green
    Write-Host "Incident:         $incidentId" -ForegroundColor Green
    Write-Host "Remediation:      $($finalReport.remediation_state)" -ForegroundColor Green
    Write-Host "Swagger UI:       $BaseUri/docs" -ForegroundColor Green
    if ($Local) {
        Write-Host "Stop local API:   .\stop-local-demo.cmd" -ForegroundColor Green
    }

    if ($OpenDocs) {
        Start-Process "$BaseUri/docs"
    }
    $demoSucceeded = $true
}
finally {
    if ($Local -and -not $demoSucceeded -and $localApiProcess -and -not $localApiProcess.HasExited) {
        Stop-Process -Id $localApiProcess.Id -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $localPidPath -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}
