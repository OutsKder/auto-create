@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%auto-create-target-projects-update"
set "FRONTEND_DIR=%ROOT%formal-create\main-site"
set "FRONTEND_URL=http://127.0.0.1:5173/drafts/console/v5"

echo.
echo ========================================
echo  Byte AI Delivery Engine - Dev Launcher
echo ========================================
echo.

if not exist "%BACKEND_DIR%" (
  echo [ERROR] Backend directory not found:
  echo %BACKEND_DIR%
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%" (
  echo [ERROR] Frontend directory not found:
  echo %FRONTEND_DIR%
  pause
  exit /b 1
)

if "%DOUBAO_API_KEY%"=="" (
  echo DOUBAO_API_KEY is not set.
  set /p "DOUBAO_API_KEY=Please paste your Doubao API key: "
)

if "%DOUBAO_API_KEY%"=="" (
  echo [ERROR] DOUBAO_API_KEY is required for real model calls.
  pause
  exit /b 1
)

set "TEST_LLM_PROVIDER=doubao"
set "CODEGEN_MAX_ATTEMPTS=5"
set "ANALYSIS_MAX_ATTEMPTS=3"

echo [1/3] Starting backend on http://127.0.0.1:8008 ...
start "Byte Backend API" cmd /k "cd /d "%BACKEND_DIR%" && set "DOUBAO_API_KEY=%DOUBAO_API_KEY%" && set "TEST_LLM_PROVIDER=%TEST_LLM_PROVIDER%" && set "CODEGEN_MAX_ATTEMPTS=%CODEGEN_MAX_ATTEMPTS%" && set "ANALYSIS_MAX_ATTEMPTS=%ANALYSIS_MAX_ATTEMPTS%" && conda run -n byte python -m backend.api_first.http_demo_server"

echo [2/3] Starting frontend on http://127.0.0.1:5173 ...
start "Byte Frontend Vite" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev -- --host 127.0.0.1 --port 5173"

echo [3/3] Opening console page ...
timeout /t 3 /nobreak >nul
start "" "%FRONTEND_URL%"

echo.
echo Started:
echo - Backend:  http://127.0.0.1:8008
echo - Frontend: http://127.0.0.1:5173
echo - Console:  %FRONTEND_URL%
echo.
echo Backend logs:
echo %BACKEND_DIR%\backend\logs\server-YYYY-MM-DD.log
echo.
echo You can close the two opened command windows to stop the services.
echo.
pause
