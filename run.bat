@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
    echo Python 3.10 or later is required. Install Python and enable the Python launcher.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" main.py
