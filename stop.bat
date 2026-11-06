@echo off
title Stop Makinity Cut Server
echo ========================================================
echo  Stopping Makinity Cut localhost server on port 8000...
echo ========================================================

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating PID: %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo Localhost on port 8000 has been stopped!
pause

