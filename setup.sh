#!/bin/bash
# Cross-platform setup script for mpx-Downloader
# This script will install all dependencies and set up the project

echo "Setting up mpx-Downloader..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed or not in PATH"
        echo "Please install Python 3.8+ from https://python.org"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Display Python version
echo "Python version:"
$PYTHON_CMD --version
echo ""

# Check Python version (requires 3.8+)
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "ERROR: Python 3.8+ is required, but found Python $PYTHON_VERSION"
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
$PYTHON_CMD -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt

# Ask about development dependencies
echo ""
read -p "Install development dependencies (for testing)? (y/n): " install_dev
if [[ $install_dev =~ ^[Yy]$ ]]; then
    echo "Installing development dependencies..."
    $PYTHON_CMD -m pip install -r requirements-dev.txt
fi

# Check if FFmpeg is available
echo ""
echo "Checking for FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is available"
    ffmpeg -version | head -1
else
    echo "WARNING: FFmpeg not found"
    echo "Installation instructions:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  CentOS/RHEL:   sudo yum install ffmpeg"
    echo "  macOS:         brew install ffmpeg"
    echo "  Windows:       winget install Gyan.FFmpeg"
    echo "  Or download from: https://ffmpeg.org/download.html"
fi

echo ""
echo "Setup completed!"
echo ""
echo "You can now run the script with:"
echo "  $PYTHON_CMD download.py"
echo ""
echo "For help, run:"
echo "  $PYTHON_CMD download.py --help"
echo ""
