$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 其他电脑若环境名不同，请改为本机可用的 conda 环境名。
$envName = "fastapi-py313"
# 需要局域网访问可改为 0.0.0.0；默认仅本机访问。
$hostAddr = "127.0.0.1"
# 端口冲突时改这里，例如 8001。
$port = "8000"

$condaExe = $env:CONDA_EXE
if (-not $condaExe) {
	# 其他电脑若未自动识别 CONDA_EXE，请改成该电脑 conda.exe 的实际路径。
	$candidate = "D:\program\miniconda3\Scripts\conda.exe"
	if (Test-Path $candidate) {
		$condaExe = $candidate
	}
}

if ($condaExe -and (Test-Path $condaExe)) {
	Write-Host "Using conda env: $envName"
	& $condaExe run -n $envName --no-capture-output python -m uvicorn main:app --host $hostAddr --port $port --reload
	exit $LASTEXITCODE
}

$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
	# 若不用 conda，可先在 backend/venv 安装依赖后走这里启动。
	Write-Host "Conda not found, using local venv at backend/venv"
	& $venvPython -m uvicorn main:app --host $hostAddr --port $port --reload
	exit $LASTEXITCODE
}

# 最后兜底使用系统 python，要求 PATH 中可找到 python 且已安装依赖。
Write-Host "Conda env not found, falling back to system python"
python -m uvicorn main:app --host $hostAddr --port $port --reload
