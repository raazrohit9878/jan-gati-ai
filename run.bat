@echo off
chcp 65001 >nul
title Jan-Gati AI Platform

echo =====================================================================
echo   Jan-Gati AI: Digital Public Good for Infrastructure and Governance
echo   Theme: AI for Digital Infrastructure and Governance
echo =====================================================================
echo.

REM Step 1: Check Python installation
python --version >nul 2>&1
if errorlevel 1 goto :no_python
goto :python_ok

:no_python
echo [ERROR] Python is not found in system PATH.
echo Please install Python 3.10+ from https://www.python.org/
echo.
pause
exit /b 1

:python_ok
echo [1/3] Python environment verified.
echo.

REM Step 2: Launch default web browser in background
echo [2/3] Launching browser at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
echo.

REM Step 3: Start FastAPI Uvicorn Server
echo [3/3] Starting Jan-Gati Server on http://127.0.0.1:8000 ...
echo ---------------------------------------------------------------------
echo   - Web Application:     http://127.0.0.1:8000
echo   - OpenAPI Swagger:     http://127.0.0.1:8000/docs
echo   - Interactive Modes:   Policymaker Cockpit / Citizen Portal / WhatsApp Bot
echo ---------------------------------------------------------------------
echo Press CTRL+C in this terminal window to stop the server.
echo.

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

if errorlevel 1 (
    echo.
    echo [ERROR] Server stopped with error code %errorlevel%.
    pause
)
