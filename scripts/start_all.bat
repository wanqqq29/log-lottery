@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "CMD=%~1"
if "%CMD%"=="" set "CMD=start"

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "BACKEND_PY=%BACKEND_DIR%\.venv\Scripts\python.exe"

set "RUN_DIR=%ROOT_DIR%\.run"
set "LOG_DIR=%RUN_DIR%\logs"
set "BACKEND_LOG=%LOG_DIR%\backend.log"
set "FRONTEND_LOG=%LOG_DIR%\frontend.log"

if not exist "%RUN_DIR%" mkdir "%RUN_DIR%" >nul 2>&1
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

if /I "%CMD%"=="start" goto :start_all
if /I "%CMD%"=="stop" goto :stop_all
if /I "%CMD%"=="restart" goto :restart_all
if /I "%CMD%"=="status" goto :status_all
if /I "%CMD%"=="help" goto :usage
if /I "%CMD%"=="--help" goto :usage
if /I "%CMD%"=="-h" goto :usage

goto :usage

:usage
echo Usage: %~nx0 [start^|stop^|restart^|status]
echo.
echo Commands:
echo   start    Start backend and frontend (default)
echo   stop     Stop backend and frontend
echo   restart  Restart backend and frontend
echo   status   Show running status
exit /b 0

:get_pid_on_port
set "%~2="
for /f %%P in ('powershell -NoProfile -Command "$p=(Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty OwningProcess); if($p){$p}"') do (
    set "%~2=%%P"
)
exit /b 0

:tail_log
if exist "%~1" (
    powershell -NoProfile -Command "Get-Content -Path '%~1' -Tail 20"
) else (
    echo Log file not found: %~1
)
exit /b 0

:start_backend
call :get_pid_on_port 8000 BACKEND_PID
if defined BACKEND_PID (
    echo [backend] Already running (PID: !BACKEND_PID!)
    exit /b 0
)

if not exist "%BACKEND_PY%" (
    echo [backend] Python venv not found: %BACKEND_PY%
    echo Please create venv first: cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

echo [backend] Starting...
start "" /b cmd /c "cd /d \"%BACKEND_DIR%\" && \"%BACKEND_PY%\" manage.py runserver 127.0.0.1:8000 --noreload >> \"%BACKEND_LOG%\" 2>&1"
timeout /t 2 >nul

call :get_pid_on_port 8000 BACKEND_PID
if defined BACKEND_PID (
    echo [backend] Started (PID: !BACKEND_PID!)
    exit /b 0
)

echo [backend] Failed to start, check log: %BACKEND_LOG%
call :tail_log "%BACKEND_LOG%"
exit /b 1

:start_frontend
call :get_pid_on_port 6719 FRONTEND_PID
if defined FRONTEND_PID (
    echo [frontend] Already running (PID: !FRONTEND_PID!)
    exit /b 0
)

where pnpm >nul 2>&1
if errorlevel 1 (
    echo [frontend] pnpm not found in PATH.
    exit /b 1
)

echo [frontend] Starting...
start "" /b cmd /c "cd /d \"%ROOT_DIR%\" && pnpm exec vite --host 127.0.0.1 --port 6719 --strictPort >> \"%FRONTEND_LOG%\" 2>&1"
timeout /t 2 >nul

call :get_pid_on_port 6719 FRONTEND_PID
if defined FRONTEND_PID (
    echo [frontend] Started (PID: !FRONTEND_PID!)
    exit /b 0
)

echo [frontend] Failed to start, check log: %FRONTEND_LOG%
call :tail_log "%FRONTEND_LOG%"
exit /b 1

:stop_backend
call :get_pid_on_port 8000 BACKEND_PID
if not defined BACKEND_PID (
    echo [backend] Not running
    exit /b 0
)

echo [backend] Stopping (PID: !BACKEND_PID!)
taskkill /PID !BACKEND_PID! /F >nul 2>&1
if errorlevel 1 (
    echo [backend] Failed to stop PID !BACKEND_PID!
    exit /b 1
)
echo [backend] Stopped
exit /b 0

:stop_frontend
call :get_pid_on_port 6719 FRONTEND_PID
if not defined FRONTEND_PID (
    echo [frontend] Not running
    exit /b 0
)

echo [frontend] Stopping (PID: !FRONTEND_PID!)
taskkill /PID !FRONTEND_PID! /F >nul 2>&1
if errorlevel 1 (
    echo [frontend] Failed to stop PID !FRONTEND_PID!
    exit /b 1
)
echo [frontend] Stopped
exit /b 0

:status_all
call :get_pid_on_port 8000 BACKEND_PID
if defined BACKEND_PID (
    echo [backend] Running (PID: !BACKEND_PID!)
) else (
    echo [backend] Not running
)

call :get_pid_on_port 6719 FRONTEND_PID
if defined FRONTEND_PID (
    echo [frontend] Running (PID: !FRONTEND_PID!)
) else (
    echo [frontend] Not running
)

exit /b 0

:start_all
set "RC=0"
call :start_backend || set "RC=1"
call :start_frontend || set "RC=1"
echo.
echo URLs:
echo - Backend API:  http://127.0.0.1:8000/api/
echo - Admin:        http://127.0.0.1:8000/admin/
echo - Frontend:     http://localhost:6719/log-lottery/
echo.
echo Logs:
echo - %BACKEND_LOG%
echo - %FRONTEND_LOG%
exit /b %RC%

:stop_all
set "RC=0"
call :stop_frontend || set "RC=1"
call :stop_backend || set "RC=1"
exit /b %RC%

:restart_all
call :stop_all
call :start_all
exit /b %errorlevel%
