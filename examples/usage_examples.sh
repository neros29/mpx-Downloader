#!/bin/bash
# Cross-platform usage examples for mpx-Downloader
# This script demonstrates various ways to use the yt-dlp wrapper

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found"
    exit 1
fi

show_menu() {
    echo "mpx-Downloader - Usage Examples"
    echo "================================"
    echo ""
    echo "Select an example to run:"
    echo ""
    echo "1. Download single video as MP3"
    echo "2. Download playlist as MKV (best seeking)"
    echo "3. Download with Firefox cookies (private playlists)"
    echo "4. Batch download from URL file"
    echo "5. Add existing files to archive"
    echo "6. Show archive information"
    echo "7. Interactive mode (default)"
    echo "8. Show more examples"
    echo "9. Exit"
    echo ""
}

while true; do
    show_menu
    read -p "Enter your choice (1-9): " choice
    echo ""
    
    case $choice in
        1)
            echo "Example 1: Download single video as MP3"
            echo "========================================"
            read -p "Enter YouTube URL: " url
            if [ ! -z "$url" ]; then
                $PYTHON_CMD download.py --format mp3 --outdir "music" "$url"
            fi
            echo ""
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "Example 2: Download playlist as MKV"
            echo "==================================="
            read -p "Enter playlist URL: " url
            if [ ! -z "$url" ]; then
                $PYTHON_CMD download.py --format mkv --outdir "videos" "$url"
            fi
            echo ""
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "Example 3: Download with Firefox cookies"
            echo "========================================"
            echo "This is useful for private playlists like YouTube Music Liked Songs"
            read -p "Enter private playlist URL: " url
            if [ ! -z "$url" ]; then
                $PYTHON_CMD download.py --firefox-cookies --format mp3 --outdir "private_music" "$url"
            fi
            echo ""
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "Example 4: Batch download from URL file"
            echo "======================================="
            echo "Make sure you have a file with URLs (one per line)"
            read -p "Enter URL file path (or press Enter for examples/urls.txt): " file
            if [ -z "$file" ]; then
                file="examples/urls.txt"
            fi
            read -p "Enter format (mp3/mkv/mp4) [mp3]: " format
            if [ -z "$format" ]; then
                format="mp3"
            fi
            $PYTHON_CMD download.py --file "$file" --format "$format" --outdir "batch_downloads"
            echo ""
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "Example 5: Add existing files to archive"
            echo "========================================"
            echo "This prevents re-downloading files you already have"
            read -p "Enter directory path to scan: " dir
            if [ ! -z "$dir" ]; then
                $PYTHON_CMD download.py --load "$dir"
            fi
            echo ""
            read -p "Press Enter to continue..."
            ;;
        6)
            echo "Example 6: Show archive information"
            echo "==================================="
            $PYTHON_CMD download.py --show-archive
            echo ""
            read -p "Press Enter to continue..."
            ;;
        7)
            echo "Example 7: Interactive mode"
            echo "==========================="
            echo "Running interactive mode (default behavior)"
            $PYTHON_CMD download.py
            echo ""
            read -p "Press Enter to continue..."
            ;;
        8)
            echo "Additional examples:"
            echo ""
            echo "# Clear archive by name"
            echo "$PYTHON_CMD download.py --clear \"Artist Name\""
            echo ""
            echo "# Clear archive by date range"
            echo "$PYTHON_CMD download.py --clear \"2024-01-01\" \"2024-12-31\""
            echo ""
            echo "# Backup archive"
            echo "$PYTHON_CMD download.py --backup"
            echo ""
            echo "# Download to specific directory"
            echo "$PYTHON_CMD download.py --format mp4 --outdir \"/home/user/Videos\" \"URL_HERE\""
            echo ""
            echo "# Download multiple URLs at once"
            echo "$PYTHON_CMD download.py --format mp3 \"URL1\" \"URL2\" \"URL3\""
            echo ""
            read -p "Press Enter to continue..."
            ;;
        9)
            echo "Thanks for using mpx-Downloader!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please enter 1-9."
            read -p "Press Enter to continue..."
            ;;
    esac
done
