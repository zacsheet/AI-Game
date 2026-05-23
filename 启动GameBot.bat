@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py"
)

if not defined PYTHON_EXE (
    echo No usable Python was found. Please install Python 3.11 or 3.12 and enable Add python.exe to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_EXE% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

set "PYTHON_EXE=.venv\Scripts\python.exe"

%PYTHON_EXE% -m pip show PyQt6 >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    %PYTHON_EXE% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

%PYTHON_EXE% -m gamebot.main
pause
