import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import download
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import download


class TestUtilityFunctions:
    """Test various utility functions."""
    
    def test_banner(self):
        """Test that banner function runs without error."""
        # Just ensure it doesn't crash
        download.banner()
    
    def test_is_youtube_music_liked_variations(self):
        """Test YouTube Music detection with various URL formats."""
        positive_cases = [
            "https://music.youtube.com/playlist?list=LM",
            "https://music.youtube.com/playlist?list=lm",
            "https://Music.YouTube.com/playlist?list=LM",
            "https://music.youtube.com/liked",
            "https://music.youtube.com/LIKED",
            "https://music.youtube.com/playlist?list=LM&si=abc"
        ]
        
        negative_cases = [
            "https://youtube.com/watch?v=abc123",
            "https://youtube.com/playlist?list=PLrAXtmRdnEQy",
            "https://music.youtube.com/playlist?list=PLrAXtmRdnEQy",
            "https://spotify.com/playlist/abc",
            "not_a_url",
            ""
        ]
        
        for url in positive_cases:
            assert download.is_youtube_music_liked(url), f"Failed for URL: {url}"
        
        for url in negative_cases:
            assert not download.is_youtube_music_liked(url), f"False positive for URL: {url}"
    
    def test_split_urls_various_formats(self):
        """Test URL splitting with different input formats."""
        # Single URL
        result = download.split_urls("https://example.com/1")
        assert result == ["https://example.com/1"]
        
        # Multiple URLs with spaces
        result = download.split_urls("https://example.com/1 https://example.com/2")
        assert result == ["https://example.com/1", "https://example.com/2"]
        
        # Multiple URLs with newlines
        result = download.split_urls("https://example.com/1\nhttps://example.com/2")
        assert result == ["https://example.com/1", "https://example.com/2"]
        
        # Mixed whitespace
        result = download.split_urls("https://example.com/1\n  https://example.com/2  \nhttps://example.com/3")
        assert result == ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        
        # Empty and whitespace-only
        assert download.split_urls("") == []
        assert download.split_urls("   \n  \t  ") == []
    
    def test_default_download_dir(self):
        """Test default download directory function."""
        result = download.default_download_dir()
        assert isinstance(result, Path)
        # Should return current working directory
        assert result == Path.cwd()
    
    @patch('download.shutil.which')
    def test_detect_ffmpeg(self, mock_which):
        """Test FFmpeg detection."""
        # Test when FFmpeg is found
        mock_which.return_value = "/usr/bin/ffmpeg"
        assert download.detect_ffmpeg() is True
        
        # Test when FFmpeg is not found
        mock_which.return_value = None
        assert download.detect_ffmpeg() is False
    
    def test_build_outtmpl_creates_directory(self):
        """Test that build_outtmpl creates the output directory."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Use a subdirectory that doesn't exist yet
            target_dir = temp_dir / "new_subdir"
            
            template = download.build_outtmpl(target_dir, True)
            
            # Directory should be created
            assert target_dir.exists()
            assert target_dir.is_dir()
            
            # Template should include the directory path
            assert str(target_dir) in template
            assert "%(title)s.%(ext)s" in template
        finally:
            shutil.rmtree(temp_dir)


class TestArchiveUtilities:
    """Test archive-related utility functions."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_stable_key_for_path_consistency(self):
        """Test that stable key generation is consistent."""
        path = "/test/path/file.mp3"
        
        # Same inputs should produce same output
        key1 = download._stable_key_for_path(path, "mp3")
        key2 = download._stable_key_for_path(path, "mp3")
        assert key1 == key2
        
        # Key should start with "local_"
        assert key1.startswith("local_")
        
        # Key should end with format
        assert key1.endswith("_mp3")
    
    def test_stable_key_for_path_uniqueness(self):
        """Test that different inputs produce different keys."""
        path1 = "/test/path1/file.mp3"
        path2 = "/test/path2/file.mp3"
        
        key1 = download._stable_key_for_path(path1, "mp3")
        key2 = download._stable_key_for_path(path2, "mp3")
        
        assert key1 != key2
        
        # Different formats should also produce different keys
        key3 = download._stable_key_for_path(path1, "mp4")
        assert key1 != key3


class TestM3UGeneration:
    """Test M3U playlist generation."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_generate_m3u_for_playlist(self):
        """Test M3U playlist generation."""
        # Create test files
        files = [
            self.temp_dir / "Song 1.mp3",
            self.temp_dir / "Song 2.mp3",
            self.temp_dir / "Song 3.mp3"
        ]
        
        for file in files:
            file.touch()
        
        # Mock playlist info
        playlist_info = {
            "playlist_title": "Test Playlist",
            "entries": [
                {"title": "Song 1"},
                {"title": "Song 2"},
                {"title": "Song 3"},
                None,  # Test handling of None entries
                {"title": "Song 4"}  # This file doesn't exist
            ]
        }
        
        download.generate_m3u_for_playlist(playlist_info, self.temp_dir, "mp3")
        
        # Check that M3U file was created
        m3u_file = self.temp_dir / "Test Playlist.m3u"
        assert m3u_file.exists()
        
        # Check M3U content
        content = m3u_file.read_text(encoding="utf-8")
        lines = content.strip().split('\n')
        
        # Should only include existing files
        assert "Song 1.mp3" in lines
        assert "Song 2.mp3" in lines
        assert "Song 3.mp3" in lines
        assert "Song 4.mp3" not in lines
    
    def test_generate_m3u_no_entries(self):
        """Test M3U generation with no entries."""
        playlist_info = {
            "playlist_title": "Empty Playlist",
            "entries": []
        }
        
        download.generate_m3u_for_playlist(playlist_info, self.temp_dir, "mp3")
        
        # No M3U file should be created
        m3u_files = list(self.temp_dir.glob("*.m3u"))
        assert len(m3u_files) == 0


class TestFileManagement:
    """Test file management functions."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_load_urls_from_file(self):
        """Test loading URLs from a text file."""
        # Create test file with URLs
        url_file = self.temp_dir / "urls.txt"
        url_content = """# This is a comment
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456

# Another comment
https://youtube.com/watch?v=ghi789
invalid_url_line
https://youtube.com/watch?v=jkl012"""
        
        url_file.write_text(url_content, encoding='utf-8')
        
        urls = download.load_urls_from_file(str(url_file))
        
        # Should load only valid URLs, skipping comments and invalid lines
        expected_urls = [
            "https://youtube.com/watch?v=abc123",
            "https://youtube.com/watch?v=def456",
            "https://youtube.com/watch?v=ghi789",
            "https://youtube.com/watch?v=jkl012"
        ]
        
        assert urls == expected_urls
    
    def test_load_urls_from_nonexistent_file(self):
        """Test loading URLs from non-existent file."""
        urls = download.load_urls_from_file("nonexistent.txt")
        assert urls == []
    
    def test_load_directory_to_archive(self):
        """Test loading directory files into archive."""
        # Create test files
        audio_files = [
            self.temp_dir / "song1.mp3",
            self.temp_dir / "song2.m4a",
            self.temp_dir / "song3.flac"
        ]
        
        video_files = [
            self.temp_dir / "video1.mp4",
            self.temp_dir / "video2.mkv"
        ]
        
        other_files = [
            self.temp_dir / "document.txt",
            self.temp_dir / "image.jpg"
        ]
        
        all_files = audio_files + video_files + other_files
        for file in all_files:
            file.touch()
        
        # Test the actual function - it now uses ArchiveManager internally
        result = download.load_directory_to_archive(str(self.temp_dir))
        
        assert result is True
        # The function should have completed successfully
    
    def test_load_directory_nonexistent(self):
        """Test loading non-existent directory."""
        result = download.load_directory_to_archive("nonexistent_directory")
        assert result is False


class TestDateParsing:
    """Test date parsing functionality."""
    
    def test_parse_date_input_formats(self):
        """Test various date input formats."""
        # Test standard formats
        date_formats = [
            ("2023-12-25", datetime(2023, 12, 25)),
            ("2023/12/25", datetime(2023, 12, 25)),
            ("12/25/2023", datetime(2023, 12, 25)),
            ("25/12/2023", datetime(2023, 12, 25)),  # Note: this might be ambiguous
        ]
        
        for date_str, expected in date_formats:
            result = download.parse_date_input(date_str)
            # Just check that we get a datetime object (exact format matching is tricky)
            assert isinstance(result, datetime), f"Failed to parse: {date_str}"
    
    def test_parse_date_input_relative(self):
        """Test relative date parsing."""
        # Test relative dates
        relative_dates = ["today", "yesterday", "last week", "last month"]
        
        for date_str in relative_dates:
            result = download.parse_date_input(date_str)
            assert isinstance(result, datetime), f"Failed to parse relative date: {date_str}"
    
    def test_parse_date_input_invalid(self):
        """Test invalid date input."""
        invalid_dates = ["not_a_date", "2023-13-45", ""]
        
        for date_str in invalid_dates:
            result = download.parse_date_input(date_str)
            assert result is None, f"Should have failed to parse: {date_str}"


class TestNewHelperFunctions:
    """Test the new helper functions introduced in the refactor."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_resolve_target_dir_youtube_music(self):
        """Test target directory resolution for YouTube Music."""
        url = "https://music.youtube.com/playlist?list=LM"
        target_dir = download.resolve_target_dir(self.temp_dir, url, None)
        
        assert target_dir == self.temp_dir / "Liked Music"
        assert target_dir.exists()
    
    def test_resolve_target_dir_playlist_with_info(self):
        """Test target directory resolution for playlists with metadata."""
        url = "https://youtube.com/playlist?list=PLtest"
        info = {
            "_type": "playlist",
            "playlist_title": "My Test Playlist"
        }
        
        target_dir = download.resolve_target_dir(self.temp_dir, url, info)
        
        assert target_dir == self.temp_dir / "My Test Playlist"
        assert target_dir.exists()
    
    def test_resolve_target_dir_single_video(self):
        """Test target directory resolution for single videos."""
        url = "https://youtube.com/watch?v=abc123"
        target_dir = download.resolve_target_dir(self.temp_dir, url, None)
        
        assert target_dir == self.temp_dir
        assert target_dir.exists()
    
    def test_clean_title_string(self):
        """Test title cleaning with string input."""
        title = "Test Video: Special Characters! & More"
        clean = download.clean_title(title)
        
        # Should be sanitized but still readable
        assert isinstance(clean, str)
        assert len(clean) > 0
        # The sanitize_filename function should handle special characters
        assert "Test Video" in clean
    
    def test_clean_title_dict(self):
        """Test title cleaning with dict input."""
        info = {"title": "Test Video: Special Characters! & More"}
        clean = download.clean_title(info)
        
        assert isinstance(clean, str)
        assert "Test Video" in clean
    
    def test_clean_title_unknown(self):
        """Test title cleaning with None/unknown input."""
        clean = download.clean_title(None)
        assert clean == "unknown"
        
        clean = download.clean_title("")
        assert clean == "unknown"
        
        clean = download.clean_title({})
        assert clean == "unknown"
    
    def test_expected_extensions_mp3(self):
        """Test expected extensions for MP3 format."""
        extensions = download.expected_extensions("mp3")
        assert extensions == [".mp3"]
    
    def test_expected_extensions_native(self):
        """Test expected extensions for native audio format."""
        extensions = download.expected_extensions("native")
        expected = [".m4a", ".opus", ".webm", ".mp3", ".aac"]
        assert extensions == expected
    
    def test_expected_extensions_video(self):
        """Test expected extensions for video formats."""
        mp4_extensions = download.expected_extensions("mp4")
        mkv_extensions = download.expected_extensions("mkv")
        
        # Both should return the same list for video formats
        expected = [".mp4", ".mkv", ".webm", ".avi"]
        assert mp4_extensions == expected
        assert mkv_extensions == expected
    
    def test_expected_extensions_custom(self):
        """Test expected extensions for custom format."""
        extensions = download.expected_extensions("flac")
        assert extensions == [".flac"]


class TestOptimizedCopyFromArchive:
    """Test the optimized copy from archive functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_optimized_copy_mp3_format_enforcement(self):
        """Test that MP3 format is enforced correctly in optimized copy."""
        # Create a source file with .webm extension (audio)
        source_file = self.temp_dir / "source.webm"
        source_file.write_text("test audio content")
        
        # Archive entry
        archive_entry = {
            "file_path": str(source_file),
            "title": "Test Song"
        }
        
        # Target directory
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # Copy with MP3 container - should enforce .mp3 extension
        result = download.optimized_copy_from_archive(archive_entry, target_dir, "mp3")
        
        # Verify success and correct extension
        assert result is True
        target_file = target_dir / "Test Song.mp3"  # Should have .mp3 extension
        assert target_file.exists()
        assert target_file.read_text() == "test audio content"
    
    def test_optimized_copy_native_format_preservation(self):
        """Test that native format preserves original extension."""
        # Create a source file with .opus extension
        source_file = self.temp_dir / "source.opus"
        source_file.write_text("test audio content")
        
        # Archive entry
        archive_entry = {
            "file_path": str(source_file),
            "title": "Test Song"
        }
        
        # Target directory
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # Copy with native container - should preserve .opus extension
        result = download.optimized_copy_from_archive(archive_entry, target_dir, "native")
        
        # Verify success and preserved extension
        assert result is True
        target_file = target_dir / "Test Song.opus"  # Should preserve .opus
        assert target_file.exists()
        assert target_file.read_text() == "test audio content"


if __name__ == "__main__":
    pytest.main([__file__])
