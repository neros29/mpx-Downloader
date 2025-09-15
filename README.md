# 🎵 Interactive yt-dlp Wrapper

An advanced, user-friendly wrapper for yt```bash
# Download audio only
python3 download.py --format mp3 "https://youtube.com/watch?v=..."

# Download video with best seeking (MKV)
python3 download.py --format mkv --outdir ./videos "https://youtube.com/playlist?list=..."

# Use Firefox cookies for private playlists
python3 download.py --firefox-cookies --format mp3 "https://music.youtube.com/playlist?list=LM"

# Load URLs from file
python3 download.py --file urls.txt --format mkv

# Add existing files to archive
python3 download.py --load ./my_music_folder

# Cross-platform batch download
chmod +x examples/batch_download.sh
./examples/batch_download.sh mp3 ~/Downloads
```features for downloading audio and video content from YouTube and other platforms.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)

## ✨ Features

- **🎛️ Interactive Mode**: Easy-to-use command-line interface with colorized output
- **📋 Smart Archive System**: Prevents re-downloading existing files and enables copying from archive
- **🎵 Multiple Formats**: Download as MP3 (audio), MKV (best seeking), or MP4 (max compatibility)
- **🍪 Cookie Support**: Automatic Firefox cookie detection for private playlists (YouTube Music Liked Songs)
- **📂 Playlist Management**: Generates M3U playlists and handles playlist updates efficiently
- **🔧 Cross-Platform**: Works on Linux, macOS, and Windows with proper path handling
- **⚡ VLC Optimized**: Enhanced seeking performance for video files
- **📊 Progress Tracking**: Real-time download progress with speed indicators

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **yt-dlp**: `pip install -U yt-dlp`
3. **FFmpeg**: 
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (CentOS/RHEL)
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or `winget install Gyan.FFmpeg`

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/neros29/mpx-Downloader.git
   cd mpx-Downloader
   ```

2. Install dependencies:
   ```bash
   # Linux/macOS
   pip3 install -r requirements.txt
   
   # Or use the setup script
   chmod +x setup.sh
   ./setup.sh
   
   # Windows
   pip install -r requirements.txt
   ```

3. Run the script:
   ```bash
   # Linux/macOS
   python3 download.py
   
   # Windows
   python download.py
   ```

## 📖 Usage

### Interactive Mode (Recommended)

Simply run the script and follow the prompts:

```bash
# Linux/macOS
python3 download.py

# Windows  
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

# Process the file (Linux/macOS)
python3 download.py --file urls.txt --format mp3

# Or use the batch script
chmod +x examples/batch_download.sh
./examples/batch_download.sh mp3 downloads

# Windows
python download.py --file urls.txt --format mp3
```

### Directory Scanning

Add existing media files to the archive to prevent re-downloading:

```bash
# Linux/macOS
python3 download.py --load "/home/user/Music"

# Windows
python download.py --load "C:\Users\Username\Music"
```

## 🛠️ Configuration

### Cookie Setup for Private Content

For YouTube Music Liked Songs and other private playlists:

1. Ensure Firefox is installed with an active YouTube session
2. Use `--firefox-cookies` flag or the script will auto-detect Liked Music URLs
3. The script automatically extracts cookies from Firefox profile

### Output Templates

Files are saved with clean, cross-platform safe filenames:
- Audio: `Title.mp3`
- Video: `Title.mkv` or `Title.mp4`
- Playlists: `PlaylistName.m3u`

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Linux/macOS
python3 -m pytest tests/
# Or use the test runner
python3 run_tests.py

# Windows
python -m pytest tests/
python run_tests.py

# Run specific test categories
python3 -m pytest tests/test_archive.py
python3 -m pytest tests/test_download.py
python3 -m pytest tests/test_utils.py
```

## 📁 Project Structure

```
mpx-downloader/
├── download.py           # Main application
├── requirements.txt      # Python dependencies
├── requirements-dev.txt  # Development dependencies
├── setup.sh             # Cross-platform setup script
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
│   ├── batch_download.sh    # Cross-platform batch script
│   └── usage_examples.sh    # Interactive examples
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
   # Linux/macOS
   pip3 install -r requirements-dev.txt
   
   # Windows
   pip install -r requirements-dev.txt
   ```
3. Run tests to ensure everything works:
   ```bash
   # Linux/macOS
   python3 -m pytest
   
   # Windows
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

- 🐛 [Report Bugs](https://github.com/neros29/mpx-Downloader/issues)
- 💡 [Request Features](https://github.com/neros29/mpx-Downloader/issues)
- 📖 [Documentation](https://github.com/neros29/mpx-Downloader/wiki)

## Archive Location

Archive files are stored in:

**Linux/macOS:**
```
~/.local/share/yt-dlp-wrapper/download_archive.json
```

**Windows:**
```
%APPDATA%\yt-dlp-wrapper\download_archive.json
```

This ensures your download history persists across different project directories.
