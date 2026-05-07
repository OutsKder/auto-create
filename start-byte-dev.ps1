$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "auto-create-target-projects-update"
$FrontendDir = Join-Path $Root "formal-create\main-site"

$BackendHost = "127.0.0.1"
$BackendPort = 8008
$FrontendHost = "0.0.0.0"
$FrontendPort = 5173
$FrontendUrl = "http://127.0.0.1:$FrontendPort/"
$CondaEnv = "byte"

$DoubaoModel = if ($env:DOUBAO_MODEL) { $env:DOUBAO_MODEL } else { "ep-20260423223020-fxwrn" }
$DoubaoApiKey = if ($env:DOUBAO_API_KEY) { $env:DOUBAO_API_KEY } else { "ark-ed75ee35-931d-4978-bdd8-4f0a9fa4e230-5f52b" }

function Resolve-Conda {
  $defaultConda = Join-Path $env:USERPROFILE "miniconda3\Scripts\conda.exe"
  if (Test-Path $defaultConda) {
    return $defaultConda
  }

  $command = Get-Command conda -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }

  throw "conda not found. Expected $defaultConda or conda in PATH."
}

function Stop-Port {
  param([int]$Port)

  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($connection in $connections) {
    $pidToStop = $connection.OwningProcess
    if ($pidToStop -and $pidToStop -ne $PID) {
      Stop-Process -Id $pidToStop -Force -ErrorAction SilentlyContinue
    }
  }
}

function Test-Port {
  param([int]$Port)

  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
    $connected = $async.AsyncWaitHandle.WaitOne(500)
    if ($connected) {
      $client.EndConnect($async)
      return $true
    }
    return $false
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Wait-Port {
  param(
    [int]$Port,
    [int]$Seconds = 25
  )

  for ($i = 0; $i -lt $Seconds; $i++) {
    if (Test-Port -Port $Port) {
      return $true
    }
    Start-Sleep -Seconds 1
  }
  return $false
}

Write-Host ""
Write-Host "========================================"
Write-Host " Byte AI Delivery Engine - One Click Start"
Write-Host "========================================"
Write-Host ""

if (!(Test-Path $BackendDir)) {
  throw "Backend directory not found: $BackendDir"
}
if (!(Test-Path $FrontendDir)) {
  throw "Frontend directory not found: $FrontendDir"
}

$CondaExe = Resolve-Conda
Write-Host "[1/5] Conda: $CondaExe"
& $CondaExe run -n $CondaEnv python -c "import langchain_core" | Out-Null

Write-Host "[2/5] Releasing ports $BackendPort and $FrontendPort ..."
Stop-Port -Port $BackendPort
Stop-Port -Port $FrontendPort
Start-Sleep -Seconds 1

$backendCommand = @"
`$env:PYTHONUTF8='1'
`$env:PYTHONIOENCODING='utf-8'
`$env:DOUBAO_API_KEY='$DoubaoApiKey'
`$env:DOUBAO_MODEL='$DoubaoModel'
`$env:TEST_LLM_PROVIDER='doubao'
`$env:CODEGEN_MAX_ATTEMPTS='5'
`$env:ANALYSIS_MAX_ATTEMPTS='3'
`$env:API_DEMO_HOST='$BackendHost'
`$env:API_DEMO_PORT='$BackendPort'
Set-Location '$BackendDir'
& '$CondaExe' run -n $CondaEnv python -m backend.api_first.http_demo_server
"@

$frontendCommand = @"
Set-Location '$FrontendDir'
npm run dev -- --host $FrontendHost --port $FrontendPort
"@

Write-Host "[3/5] Starting backend on http://$BackendHost`:$BackendPort ..."
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) -WindowStyle Normal

if (!(Wait-Port -Port $BackendPort -Seconds 30)) {
  Write-Host "[ERROR] Backend did not start on port $BackendPort." -ForegroundColor Red
  Write-Host "Please check the opened 'Byte Backend API' PowerShell window for the first error."
  pause
  exit 1
}

Write-Host "[4/5] Starting frontend on http://127.0.0.1:$FrontendPort ..."
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand) -WindowStyle Normal

if (!(Wait-Port -Port $FrontendPort -Seconds 30)) {
  Write-Host "[ERROR] Frontend did not start on port $FrontendPort." -ForegroundColor Red
  Write-Host "Please check the opened 'Byte Frontend Vite' PowerShell window for the first error."
  pause
  exit 1
}

Write-Host "[5/5] Opening final product site ..."
Start-Process $FrontendUrl

Write-Host ""
Write-Host "Started:"
Write-Host "- Backend:  http://127.0.0.1:$BackendPort"
Write-Host "- Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "- Product:  $FrontendUrl"
Write-Host ""
Write-Host "Final user flow: Product Site -> Login -> Role Selection -> Console"
Write-Host "Backend logs: $BackendDir\backend\logs\server-YYYY-MM-DD.log"
Write-Host ""
Read-Host "Press Enter to close this launcher window. Service windows will keep running"
