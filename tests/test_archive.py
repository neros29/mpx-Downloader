import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open
import sys
import os

# Add the parent directory to the path so we can import download
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import download


class TestArchiveFunctions:
    """Test archive-related functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.archive_file = self.temp_dir / "test_archive.json"
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('download.get_appdata_archive_path')
    def test_load_archive_empty(self, mock_path):
        """Test loading an empty/non-existent archive."""
        mock_path.return_value = self.archive_file
        archive = download.load_archive()
        assert archive == {}
    
    @patch('download.get_appdata_archive_path')
    def test_load_archive_existing(self, mock_path):
        """Test loading an existing archive."""
        mock_path.return_value = self.archive_file
        
        # Create test archive data
        test_data = {
            "youtube_abc123_mp3": {
                "id": "abc123",
                "extractor": "youtube",
                "title": "Test Video",
                "format": "mp3",
                "file_path": str(self.temp_dir / "test.mp3"),
                "download_date": 1234567890.0
            }
        }
        
        # Write test data to file
        with self.archive_file.open('w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        archive = download.load_archive()
        assert archive == test_data
    
    @patch('download.get_appdata_archive_path')
    def test_save_archive(self, mock_path):
        """Test saving archive data."""
        mock_path.return_value = self.archive_file
        
        test_data = {
            "test_key": {
                "id": "test123",
                "title": "Test Title"
            }
        }
        
        download.save_archive(test_data)
        
        # Verify the file was created and contains correct data
        assert self.archive_file.exists()
        with self.archive_file.open('r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == test_data
    
    @patch('download.get_appdata_archive_path')
    def test_add_to_archive(self, mock_path):
        """Test adding entries to archive."""
        mock_path.return_value = self.archive_file
        
        # Create a test file
        test_file = self.temp_dir / "test.mp3"
        test_file.touch()
        
        download.add_to_archive("abc123", "youtube", "Test Video", test_file, "mp3")
        
        # Verify the entry was added
        archive = download.load_archive()
        key = "youtube_abc123_mp3"
        assert key in archive
        assert archive[key]["id"] == "abc123"
        assert archive[key]["title"] == "Test Video"
        assert archive[key]["format"] == "mp3"
    
    @patch('download.get_appdata_archive_path')
    def test_find_in_archive_existing(self, mock_path):
        """Test finding existing entry in archive."""
        mock_path.return_value = self.archive_file
        
        # Create test file and add to archive
        test_file = self.temp_dir / "test.mp3"
        test_file.touch()
        download.add_to_archive("abc123", "youtube", "Test Video", test_file, "mp3")
        
        # Find the entry
        entry = download.find_in_archive("abc123", "youtube", "mp3")
        assert entry is not None
        assert entry["id"] == "abc123"
        assert entry["title"] == "Test Video"
    
    @patch('download.get_appdata_archive_path')
    def test_find_in_archive_missing_file(self, mock_path):
        """Test finding entry with missing file (should be removed)."""
        mock_path.return_value = self.archive_file
        
        # Create archive entry without actual file
        test_data = {
            "youtube_abc123_mp3": {
                "id": "abc123",
                "extractor": "youtube",
                "title": "Test Video",
                "format": "mp3",
                "file_path": str(self.temp_dir / "nonexistent.mp3"),
                "download_date": 1234567890.0
            }
        }
        download.save_archive(test_data)
        
        # Try to find the entry (should return None and remove from archive)
        entry = download.find_in_archive("abc123", "youtube", "mp3")
        assert entry is None
        
        # Verify entry was removed from archive
        archive = download.load_archive()
        assert "youtube_abc123_mp3" not in archive


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_is_youtube_music_liked(self):
        """Test YouTube Music Liked playlist detection."""
        # Test positive cases
        assert download.is_youtube_music_liked("https://music.youtube.com/playlist?list=LM")
        assert download.is_youtube_music_liked("https://music.youtube.com/playlist?list=lm")
        assert download.is_youtube_music_liked("https://music.youtube.com/liked")
        
        # Test negative cases
        assert not download.is_youtube_music_liked("https://youtube.com/watch?v=abc123")
        assert not download.is_youtube_music_liked("https://music.youtube.com/playlist?list=PLrAXtmRdnEQy")
    
    def test_split_urls(self):
        """Test URL splitting functionality."""
        # Test single URL
        urls = download.split_urls("https://youtube.com/watch?v=abc123")
        assert urls == ["https://youtube.com/watch?v=abc123"]
        
        # Test multiple URLs with spaces
        urls = download.split_urls("https://youtube.com/watch?v=abc123 https://youtube.com/watch?v=def456")
        assert len(urls) == 2
        assert urls[0] == "https://youtube.com/watch?v=abc123"
        assert urls[1] == "https://youtube.com/watch?v=def456"
        
        # Test multiple URLs with newlines
        urls = download.split_urls("https://youtube.com/watch?v=abc123\nhttps://youtube.com/watch?v=def456")
        assert len(urls) == 2
        
        # Test empty string
        urls = download.split_urls("")
        assert urls == []
    
    def test_detect_ffmpeg(self):
        """Test FFmpeg detection."""
        # This test will depend on whether FFmpeg is actually installed
        # Just verify the function runs without error
        result = download.detect_ffmpeg()
        assert isinstance(result, bool)
    
    def test_default_download_dir(self):
        """Test default download directory."""
        default_dir = download.default_download_dir()
        assert isinstance(default_dir, Path)
        assert default_dir.exists()  # Should be current working directory
    
    def test_choose_format_validation(self):
        """Test format choice tuple structure."""
        # This would need to be tested with mocked input
        # For now, just test that the function exists
        assert callable(download.choose_format)
    
    def test_build_outtmpl(self):
        """Test output template building."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Test audio template
            template = download.build_outtmpl(temp_dir, True)
            assert str(temp_dir) in template
            assert "%(title)s.%(ext)s" in template
            
            # Test video template
            template = download.build_outtmpl(temp_dir, False)
            assert str(temp_dir) in template
            assert "%(title)s.%(ext)s" in template
        finally:
            shutil.rmtree(temp_dir)


class TestArchivePathFunctions:
    """Test archive path-related functions."""
    
    def test_get_appdata_archive_path(self):
        """Test getting AppData archive path."""
        path = download.get_appdata_archive_path()
        assert isinstance(path, Path)
        assert path.name == "download_archive.json"
        assert "yt-dlp-wrapper" in str(path)
    
    def test_stable_key_for_path(self):
        """Test stable key generation for file paths."""
        # Test that same path generates same key
        path = "/test/path/file.mp3"
        key1 = download._stable_key_for_path(path, "mp3")
        key2 = download._stable_key_for_path(path, "mp3")
        assert key1 == key2
        
        # Test that different paths generate different keys
        path2 = "/test/path/different.mp3"
        key3 = download._stable_key_for_path(path2, "mp3")
        assert key1 != key3
        
        # Test that different formats generate different keys
        key4 = download._stable_key_for_path(path, "mp4")
        assert key1 != key4


class TestCommandLineArgs:
    """Test command line argument parsing."""
    
    def test_parse_args_empty(self):
        """Test parsing empty arguments."""
        args = download.parse_args([])
        assert args["help"] is False
        assert args["format"] is None
        assert args["urls"] == []
    
    def test_parse_args_help(self):
        """Test help flag parsing."""
        args = download.parse_args(["--help"])
        assert args["help"] is True
        
        args = download.parse_args(["-h"])
        assert args["help"] is True
    
    def test_parse_args_format(self):
        """Test format argument parsing."""
        args = download.parse_args(["--format", "mp3"])
        assert args["format"] == "mp3"
        
        args = download.parse_args(["--format", "mkv"])
        assert args["format"] == "mkv"
    
    def test_parse_args_outdir(self):
        """Test output directory argument parsing."""
        args = download.parse_args(["--outdir", "/test/path"])
        assert args["outdir"] == "/test/path"
    
    def test_parse_args_firefox_cookies(self):
        """Test Firefox cookies flag parsing."""
        args = download.parse_args(["--firefox-cookies"])
        assert args["firefox_cookies"] is True
    
    def test_parse_args_urls(self):
        """Test URL argument parsing."""
        args = download.parse_args(["https://youtube.com/watch?v=abc123"])
        assert "https://youtube.com/watch?v=abc123" in args["urls"]
        
        args = download.parse_args(["url1", "url2", "url3"])
        assert len(args["urls"]) == 3
    
    def test_parse_args_mixed(self):
        """Test parsing mixed arguments."""
        args = download.parse_args([
            "--format", "mp3",
            "--outdir", "/downloads",
            "--firefox-cookies",
            "https://youtube.com/watch?v=abc123"
        ])
        assert args["format"] == "mp3"
        assert args["outdir"] == "/downloads"
        assert args["firefox_cookies"] is True
        assert "https://youtube.com/watch?v=abc123" in args["urls"]


if __name__ == "__main__":
    pytest.main([__file__])
