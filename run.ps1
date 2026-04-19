$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $projectRoot "backend\run.ps1"

if (-not (Test-Path $runner)) {
  Write-Error "Cannot find startup script: $runner"
  exit 1
}

& $runner
exit $LASTEXITCODE
