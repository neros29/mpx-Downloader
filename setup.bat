@echo off
REM Quick setup script for Windows
REM This script will install all dependencies and set up the project

echo Setting up yt-dlp Wrapper...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Display Python version
echo Python version:
python --version
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
python -m pip install -r requirements.txt

REM Install development dependencies (optional)
echo.
set /p install_dev="Install development dependencies (for testing)? (y/n): "
if /i "%install_dev%"=="y" (
    echo Installing development dependencies...
    python -m pip install -r requirements-dev.txt
)

REM Check if FFmpeg is available
echo.
echo Checking for FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg not found
    echo You can install it with: winget install Gyan.FFmpeg
    echo Or download from: https://ffmpeg.org/download.html
) else (
    echo FFmpeg is available
)

echo.
echo Setup completed!
echo.
echo You can now run the script with:
echo   python download.py
echo.
echo For help, run:
echo   python download.py --help
echo.
pause
