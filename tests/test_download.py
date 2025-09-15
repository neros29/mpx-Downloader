import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add the parent directory to the path so we can import download
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import download


class TestDownloadFunctions:
    """Test download-related functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_info = {
            "id": "abc123",
            "title": "Test Video Title",
            "extractor": "youtube",
            "extractor_key": "Youtube"
        }
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_check_existing_file(self):
        """Test checking for existing files."""
        # Create a test file
        test_file = self.temp_dir / "Test Video Title.mp3"
        test_file.touch()
        
        # Test that it finds existing MP3
        exists = download.check_existing_file(self.temp_dir, self.test_info, "mp3")
        assert exists is True
        
        # Test that it doesn't find non-existent file
        exists = download.check_existing_file(self.temp_dir, {"title": "Non-existent"}, "mp3")
        assert exists is False
    
    def test_check_existing_file_video_formats(self):
        """Test checking for existing video files with different extensions."""
        # Create test files with different extensions
        test_files = [
            self.temp_dir / "Test Video Title.mp4",
            self.temp_dir / "Test Video Title.mkv",
            self.temp_dir / "Test Video Title.webm"
        ]
        
        for test_file in test_files:
            test_file.touch()
            
            # Should find the file regardless of requested container
            exists = download.check_existing_file(self.temp_dir, self.test_info, "mp4")
            assert exists is True
            
            # Clean up for next iteration
            test_file.unlink()
    
    def test_folder_name_from_info(self):
        """Test folder name generation from video info."""
        # Test with playlist title
        info = {"playlist_title": "My Playlist"}
        name = download.folder_name_from_info(info)
        assert name == "My Playlist"
        
        # Test with uploader
        info = {"uploader": "Test Channel"}
        name = download.folder_name_from_info(info)
        assert name == "Test Channel"
        
        # Test with channel
        info = {"channel": "Test Channel Name"}
        name = download.folder_name_from_info(info)
        assert name == "Test Channel Name"
        
        # Test with unknown
        info = {}
        name = download.folder_name_from_info(info)
        assert name == "Unknown"
    
    @patch('download.build_archive_from_existing_files')
    @patch('download.SmartYoutubeDL')
    def test_download_urls_basic(self, mock_ydl_class, mock_build_archive):
        """Test basic URL downloading functionality."""
        # Mock the YoutubeDL instance
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=None)
        mock_ydl.download.return_value = 0
        mock_ydl.downloaded_count = 1
        mock_ydl.copied_count = 0
        mock_ydl.skipped_count = 0
        mock_ydl.extract_info.return_value = {"_type": "video"}
        mock_ydl_class.return_value = mock_ydl
        
        # Test download
        urls = ["https://youtube.com/watch?v=abc123"]
        result = download.download_urls(urls, self.temp_dir, "mp3", "audio", False)
        
        # Verify YoutubeDL was called correctly
        mock_ydl_class.assert_called_once()
        mock_ydl.download.assert_called_once_with(urls)
        assert result == 1  # One successful download
    
    @patch('download.build_archive_from_existing_files')
    @patch('download.SmartYoutubeDL')
    def test_download_urls_youtube_music_auto_cookies(self, mock_ydl_class, mock_build_archive):
        """Test automatic cookie enabling for YouTube Music in immediate mode."""
        # Mock the SmartYoutubeDL instance used in immediate mode
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=None)
        mock_ydl.download.return_value = 0
        mock_ydl.downloaded_count = 1
        mock_ydl.copied_count = 0
        mock_ydl.skipped_count = 0
        mock_ydl_class.return_value = mock_ydl
        
        # Test with YouTube Music Liked URL
        urls = ["https://music.youtube.com/playlist?list=LM"]
        download.download_urls(urls, self.temp_dir, "mp3", "audio", False)
        
        # Verify SmartYoutubeDL was called with options that include cookies
        mock_ydl_class.assert_called_once()
        call_args = mock_ydl_class.call_args[0]  # Get positional arguments
        opts = call_args[0]  # First argument should be the options dict
        
        # Verify cookies were auto-enabled in the options
        assert "cookiesfrombrowser" in opts
        assert opts["cookiesfrombrowser"] == ("firefox", None, None, None)
    
    @patch('download.build_archive_from_existing_files')
    @patch('download.YoutubeDL')
    @patch('download.SmartYoutubeDL')
    def test_download_urls_retry_with_cookies(self, mock_ydl_class, mock_temp_ydl_class, mock_build_archive):
        """Test automatic retry with cookies when playlist access fails."""
        # Mock the temporary YoutubeDL for info extraction to fail first
        mock_temp_ydl = MagicMock()
        mock_temp_ydl.extract_info.side_effect = Exception("This playlist is private")
        mock_temp_ydl_class.return_value = mock_temp_ydl
        
        # Mock the first SmartYoutubeDL instance to fail
        mock_ydl_fail = MagicMock()
        mock_ydl_fail.__enter__ = MagicMock(return_value=mock_ydl_fail)
        mock_ydl_fail.__exit__ = MagicMock(return_value=None)
        mock_ydl_fail.download.side_effect = Exception("This playlist is private")
        
        # Mock the retry SmartYoutubeDL instance to succeed
        mock_ydl_success = MagicMock()
        mock_ydl_success.__enter__ = MagicMock(return_value=mock_ydl_success)
        mock_ydl_success.__exit__ = MagicMock(return_value=None)
        mock_ydl_success.download.return_value = 0
        mock_ydl_success.downloaded_count = 1
        mock_ydl_success.copied_count = 0
        mock_ydl_success.skipped_count = 0
        
        # Set up mock to return failing instance first, then success instance
        mock_ydl_class.side_effect = [mock_ydl_fail, mock_ydl_success]
        
        # Test with a private playlist URL
        urls = ["https://youtube.com/playlist?list=PLprivate123"]
        result = download.download_urls(urls, self.temp_dir, "mp3", "audio", False)
        
        # Verify that both instances were created (original + retry)
        assert mock_ydl_class.call_count == 2
        # Verify the retry succeeded
        assert result == 1
    
    def test_ydl_opts_common_audio(self):
        """Test yt-dlp options for audio downloads."""
        opts = download.ydl_opts_common(self.temp_dir, "mp3", "audio", False)
        
        assert "format" in opts
        assert opts["format"] == "bestaudio/best"
        assert "postprocessors" in opts
        
        # Check for audio-specific postprocessors
        pp_keys = [pp["key"] for pp in opts["postprocessors"]]
        assert "FFmpegExtractAudio" in pp_keys
        assert "EmbedThumbnail" in pp_keys
        assert "FFmpegMetadata" in pp_keys
    
    def test_ydl_opts_common_video_mkv(self):
        """Test yt-dlp options for MKV video downloads."""
        opts = download.ydl_opts_common(self.temp_dir, "mkv", "video", False)
        
        assert "format" in opts
        assert "bestvideo+bestaudio" in opts["format"]
        assert opts["merge_output_format"] == "mkv"
        
        # Check for video-specific postprocessors
        pp_keys = [pp["key"] for pp in opts["postprocessors"]]
        assert "FFmpegMetadata" in pp_keys
        assert "EmbedThumbnail" in pp_keys
    
    def test_ydl_opts_common_video_mp4(self):
        """Test yt-dlp options for MP4 video downloads."""
        opts = download.ydl_opts_common(self.temp_dir, "mp4", "video", False)
        
        assert "format" in opts
        assert opts["merge_output_format"] == "mp4"
        
        # Check for MP4-specific optimizations
        assert "+faststart" in " ".join(opts["postprocessor_args"])
    
    def test_ydl_opts_common_with_cookies(self):
        """Test yt-dlp options with Firefox cookies enabled."""
        opts = download.ydl_opts_common(self.temp_dir, "mp3", "audio", True)
        
        assert "cookiesfrombrowser" in opts
        assert opts["cookiesfrombrowser"] == ("firefox", None, None, None)


class TestSmartYoutubeDL:
    """Test the custom SmartYoutubeDL class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('download.copy_from_archive')
    def test_process_info_copy_from_archive(self, mock_copy):
        """Test copying file from archive instead of downloading."""
        # Setup mocks
        mock_copy.return_value = True
        
        # Create SmartYoutubeDL instance with a mocked archive manager
        ydl = download.SmartYoutubeDL({}, self.temp_dir, "mp3")
        
        # Mock the archive manager's find method
        from unittest.mock import MagicMock
        mock_archive_entry = {"file_path": "/path/to/file.mp3"}
        ydl.archive.find = MagicMock(return_value=mock_archive_entry)
        
        # Test info dict
        info_dict = {
            "id": "abc123",
            "extractor_key": "Youtube",
            "title": "Test Video"
        }
        
        # Process the info
        result = ydl.process_info(info_dict)
        
        # Should return None (skip download) and increment copied count
        assert result is None
        assert ydl.copied_count == 1
        ydl.archive.find.assert_called_once_with("abc123", "Youtube", "mp3", "Test Video")
        mock_copy.assert_called_once()
    
    @patch('download.check_existing_file')
    def test_process_info_skip_existing(self, mock_check):
        """Test skipping existing files."""
        # Setup mock
        mock_check.return_value = True
        
        # Create SmartYoutubeDL instance
        ydl = download.SmartYoutubeDL({}, self.temp_dir, "mp3")
        
        # Test info dict
        info_dict = {
            "id": "abc123",
            "extractor_key": "Youtube",
            "title": "Test Video"
        }
        
        # Process the info
        result = ydl.process_info(info_dict)
        
        # Should return None (skip download) and increment skipped count
        assert result is None
        assert ydl.skipped_count == 1


class TestFileOperations:
    """Test file operation functions."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_copy_from_archive_success(self):
        """Test successful copying from archive."""
        # Create source file
        source_file = self.temp_dir / "source.mp3"
        source_file.write_text("test content")
        
        # Archive entry
        archive_entry = {
            "file_path": str(source_file),
            "title": "Test Song"
        }
        
        # Target directory
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # Copy from archive
        result = download.copy_from_archive(archive_entry, target_dir, "mp3")
        
        # Verify success
        assert result is True
        target_file = target_dir / "Test Song.mp3"
        assert target_file.exists()
        assert target_file.read_text() == "test content"
    
    def test_copy_from_archive_missing_source(self):
        """Test copying when source file doesn't exist."""
        # Archive entry with non-existent file
        archive_entry = {
            "file_path": str(self.temp_dir / "nonexistent.mp3"),
            "title": "Test Song"
        }
        
        # Target directory
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # Attempt to copy
        result = download.copy_from_archive(archive_entry, target_dir, "mp3")
        
        # Should fail
        assert result is False
    
    def test_build_archive_from_existing_files(self):
        """Test building archive from existing files in directory."""
        # Create test files
        test_files = [
            self.temp_dir / "song1.mp3",
            self.temp_dir / "song2.mp3",
            self.temp_dir / "video1.mp4"
        ]
        
        for file in test_files:
            file.touch()
        
        with patch('download.load_archive', return_value={}), \
             patch('download.save_archive') as mock_save:
            
            download.build_archive_from_existing_files(self.temp_dir, "mp3")
            
            # Verify save_archive was called
            mock_save.assert_called_once()
            
            # Get the archive data that would be saved
            saved_archive = mock_save.call_args[0][0]
            
            # Should have entries for MP3 files only (since container is "mp3")
            mp3_entries = [k for k in saved_archive.keys() if "mp3" in str(saved_archive[k].get("file_path", ""))]
            assert len(mp3_entries) == 2


if __name__ == "__main__":
    pytest.main([__file__])
