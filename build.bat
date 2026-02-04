@echo off
setlocal

:: ============================================================================
:: Script to build the Stock Control application for Windows
:: ============================================================================

:: --- Configuration ---
set REPO_URL=https://github.com/your-username/your-repo.git
set REPO_DIR=stock-control-app
set SCRIPT_NAME=main.py
set ICON_PATH=assets/icon.ico

:: --- Prerequisites Check ---
echo Checking prerequisites...

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Git is not installed or not in the system's PATH.
    echo Please install Git from https://git-scm.com/ and try again.
    goto :eof
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in the system's PATH.
    echo Please install Python from https://www.python.org/ and try again.
    goto :eof
)

echo.
echo --- Cloning Repository ---
if exist "%REPO_DIR%" (
    echo Repository directory '%REPO_DIR%' already exists. Skipping clone.
) else (
    git clone %REPO_URL% %REPO_DIR%
    if %errorlevel% neq 0 (
        echo Error: Failed to clone repository.
        goto :eof
    )
)

cd %REPO_DIR%

echo.
echo --- Installing Dependencies ---
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    goto :eof
)

echo.
echo --- Building Executable ---
pyinstaller --onefile --windowed --name="StockControl" --icon="%ICON_PATH%" "%SCRIPT_NAME%"
if %errorlevel% neq 0 (
    echo Error: PyInstaller failed to build the executable.
    goto :eof
)

echo.
echo --- Build Successful! ---
echo The executable can be found in the 'dist' folder.

endlocal
