# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-14

### Added
- Initial release of Interactive yt-dlp Wrapper
- Smart archive system to prevent duplicate downloads
- Support for MP3 (audio), MKV (video), and MP4 (video) formats
- Automatic Firefox cookie detection for YouTube Music
- Interactive command-line interface with colorized output
- Batch processing with URL files
- M3U playlist generation
- Archive management (backup, clear by name/date)
- Directory scanning to add existing files to archive
- VLC-optimized video settings for better seeking
- Cross-platform safe filename handling
- Comprehensive test suite
- Complete documentation and examples
- Cross-platform shell scripts for setup and batch operations

### Features
- **Interactive Mode**: Easy-to-use prompts for all options
- **Command Line Mode**: Full automation support with flags
- **Smart Downloads**: Copy from archive instead of re-downloading
- **Cookie Support**: Automatic private playlist access
- **Progress Tracking**: Real-time download progress and speed
- **Error Recovery**: Robust error handling and retries
- **Archive System**: JSON-based download tracking in AppData
- **Format Options**: Audio-only, video with best seeking, or max compatibility
- **Batch Processing**: Process multiple URLs from files
- **Playlist Support**: Generate M3U files with proper ordering

### Technical Details
- Minimum Python version: 3.8+
- Cross-platform support: Linux, macOS, Windows
- Uses yt-dlp as the download engine
- FFmpeg integration for audio/video processing
- Colorama for cross-platform terminal colors
- JSON-based archive storage in platform-appropriate directories
- Comprehensive error handling and logging
- Unit tests with pytest framework

### Documentation
- Complete README with usage examples
- Contributing guidelines
- MIT License
- Setup instructions and requirements
- API documentation in code
- Example configurations and batch files

[1.0.0]: https://github.com/neros29/mpx-Downloader/releases/tag/v1.0.0
