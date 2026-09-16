@echo off
title Jan-Gati AI Platform - Test Suite
chcp 65001 >nul
echo =====================================================================
echo   Running Jan-Gati AI Automated Verification Test Suite
echo =====================================================================
echo.

python -m pytest tests/ -v

echo.
echo =====================================================================
echo Test execution completed.
echo =====================================================================
pause
