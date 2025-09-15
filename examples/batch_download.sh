#!/bin/bash
# Cross-platform batch download script for mpx-Downloader
# Usage: ./batch_download.sh [format] [output_directory]

# Default values
FORMAT=${1:-mp3}
OUTDIR=${2:-downloads}

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found"
    exit 1
fi

echo "Starting batch download..."
echo "Format: $FORMAT"
echo "Output Directory: $OUTDIR"
echo ""

# Create output directory if it doesn't exist
mkdir -p "$OUTDIR"

# Check if URL file exists
if [ ! -f "examples/urls.txt" ]; then
    echo "ERROR: examples/urls.txt not found"
    echo "Please create a file with URLs (one per line)"
    exit 1
fi

# Run the download script
$PYTHON_CMD download.py --file examples/urls.txt --format "$FORMAT" --outdir "$OUTDIR"

echo ""
echo "Batch download completed!"
echo "Files saved to: $OUTDIR"
