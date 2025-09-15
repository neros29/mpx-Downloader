# 🎵 Interactive yt-dlp Wrapper

An advanced, user-friendly wrapper for yt-dlp with smart features for downloading audio and video content from YouTube and other platforms.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

## ✨ Features

- **🎛️ Interactive Mode**: Easy-to-use command-line interface with colorized output
- **📋 Smart Archive System**: Prevents re-downloading existing files and enables copying from archive
- **🎵 Multiple Formats**: Download as MP3 (audio), MKV (best seeking), or MP4 (max compatibility)
- **🍪 Cookie Support**: Automatic Firefox cookie detection for private playlists (YouTube Music Liked Songs)
- **📂 Playlist Management**: Generates M3U playlists and handles playlist updates efficiently
- **🔧 Windows Optimized**: Safe filenames, robust error handling, and AppData archive storage
- **⚡ VLC Optimized**: Enhanced seeking performance for video files
- **📊 Progress Tracking**: Real-time download progress with speed indicators

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **yt-dlp**: `pip install -U yt-dlp`
3. **FFmpeg**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or install via winget:
   ```bash
   winget install Gyan.FFmpeg
   ```

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/yt-dlp-wrapper.git
   cd yt-dlp-wrapper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the script:
   ```bash
   python download.py
   ```

## 📖 Usage

### Interactive Mode (Recommended)

Simply run the script and follow the prompts:

```bash
python download.py
```

### Command Line Mode

```bash
# Download audio only
python download.py --format mp3 "https://youtube.com/watch?v=..."

# Download video with best seeking (MKV)
python download.py --format mkv --outdir ./videos "https://youtube.com/playlist?list=..."

# Use Firefox cookies for private playlists
python download.py --firefox-cookies --format mp3 "https://music.youtube.com/playlist?list=LM"

# Load URLs from file
python download.py --file urls.txt --format mkv

# Add existing files to archive
python download.py --load ./my_music_folder
```

### Available Options

| Option | Description |
|--------|-------------|
| `--help` | Show help message and exit |
| `--format FORMAT` | Download format: mp3, mkv, mp4 (default: interactive) |
| `--outdir PATH` | Output directory (default: current directory) |
| `--firefox-cookies` | Use Firefox cookies for authentication |
| `--file FILE` | Read URLs from text file (one per line) |
| `--load DIRECTORY` | Scan directory and add existing files to archive |
| `--show-archive` | Display archive information |
| `--backup` | Create backup of download archive |
| `--clear [OPTIONS]` | Clear archive entries (all, by name, or by date) |

### Format Options

- **MP3**: Audio only with embedded thumbnails
- **MKV**: Video with best seeking performance and embedded thumbnails
- **MP4**: Video with maximum compatibility

## 🔧 Advanced Features

### Archive Management

The script maintains a smart archive system in your AppData folder that:
- Prevents duplicate downloads
- Enables copying existing files instead of re-downloading
- Tracks download history and file locations
- Supports format-specific tracking (MP3 vs MP4 vs MKV)

#### Archive Commands

```bash
# View archive information
python download.py --show-archive

# Create backup
python download.py --backup

# Clear by name/title
python download.py --clear "Artist Name"

# Clear by date range
python download.py --clear "2024-01-01" "2024-12-31"

# Clear everything (with confirmation)
python download.py --clear all
```

### Batch Processing

Create a text file with URLs (one per line) and process them all:

```bash
# urls.txt
https://youtube.com/watch?v=video1
https://youtube.com/watch?v=video2
https://youtube.com/playlist?list=playlist1

# Process the file
python download.py --file urls.txt --format mp3
```

### Directory Scanning

Add existing media files to the archive to prevent re-downloading:

```bash
python download.py --load "C:\Users\Username\Music"
```

## 🛠️ Configuration

### Cookie Setup for Private Content

For YouTube Music Liked Songs and other private playlists:

1. Ensure Firefox is installed with an active YouTube session
2. Use `--firefox-cookies` flag or the script will auto-detect Liked Music URLs
3. The script automatically extracts cookies from Firefox profile

### Output Templates

Files are saved with clean, Windows-safe filenames:
- Audio: `Title.mp3`
- Video: `Title.mkv` or `Title.mp4`
- Playlists: `PlaylistName.m3u`

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_archive.py
python -m pytest tests/test_download.py
python -m pytest tests/test_utils.py
```

## 📁 Project Structure

```
yt-dlp-wrapper/
├── download.py           # Main application
├── requirements.txt      # Python dependencies
├── requirements-dev.txt  # Development dependencies
├── README.md            # This file
├── LICENSE              # MIT license
├── .gitignore           # Git ignore rules
├── setup.py             # Package setup
├── tests/               # Test suite
│   ├── __init__.py
│   ├── test_archive.py
│   ├── test_download.py
│   └── test_utils.py
├── examples/            # Example configurations
│   ├── urls.txt
│   └── batch_download.bat
└── docs/                # Additional documentation
    ├── CONTRIBUTING.md
    └── CHANGELOG.md
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

### Development Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Run tests to ensure everything works:
   ```bash
   python -m pytest
   ```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The amazing download engine
- [FFmpeg](https://ffmpeg.org/) - Media processing framework
- [colorama](https://github.com/tartley/colorama) - Cross-platform colored terminal text

## 🔗 Links

- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp#readme)
- [FFmpeg Download](https://ffmpeg.org/download.html)
- [Python Downloads](https://www.python.org/downloads/)

## 🐛 Issues & Support

- 🐛 [Report Bugs](https://github.com/yourusername/yt-dlp-wrapper/issues)
- 💡 [Request Features](https://github.com/yourusername/yt-dlp-wrapper/issues)
- 📖 [Documentation](https://github.com/yourusername/yt-dlp-wrapper/wiki)

## 📊 Archive Location

Archive files are stored in:
```
%APPDATA%\yt-dlp-wrapper\download_archive.json
```

This ensures your download history persists across different project directories.
