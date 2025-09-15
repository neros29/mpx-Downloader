"""
Integration tests for the refactored download system.

These tests ensure that all the new helper functions and ArchiveManager
work together correctly in realistic scenarios.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import download
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import download


class TestEndToEndIntegration:
    """Test complete end-to-end functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.archive_file = self.temp_dir / "test_archive.json"
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('download.get_appdata_archive_path')
    def test_complete_archive_workflow(self, mock_path):
        """Test complete workflow: build archive, find entries, copy files."""
        mock_path.return_value = self.archive_file
        
        # Create test files
        test_files = [
            self.temp_dir / "Test Song 1.mp3",
            self.temp_dir / "Test Song 2.mp3",
            self.temp_dir / "Test Video.mp4"
        ]
        
        for file in test_files:
            file.write_text(f"content of {file.name}")
        
        # Step 1: Build archive from existing files
        archive_mgr = download.ArchiveManager()
        download.build_archive_from_existing_files_optimized(self.temp_dir, "mp3", archive_mgr)
        
        # Verify archive was built correctly
        assert len(archive_mgr.data) >= 2  # At least the MP3 files
        assert archive_mgr._dirty
        
        # Step 2: Save and reload archive
        archive_mgr.save()
        assert not archive_mgr._dirty
        assert self.archive_file.exists()
        
        # Reload archive in new manager
        new_archive_mgr = download.ArchiveManager()
        assert len(new_archive_mgr.data) == len(archive_mgr.data)
        
        # Step 3: Test finding and copying
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # Find an entry and copy it
        for key, entry in new_archive_mgr.data.items():
            if entry['format'] == 'mp3':
                result = download.optimized_copy_from_archive(entry, target_dir, "mp3")
                assert result is True
                
                # Verify file was copied correctly
                title = download.clean_title(entry['title'])
                target_file = target_dir / f"{title}.mp3"
                assert target_file.exists()
                break
    
    def test_helper_functions_integration(self):
        """Test that all helper functions work together."""
        # Test resolve_target_dir with different scenarios
        
        # YouTube Music
        ym_dir = download.resolve_target_dir(self.temp_dir, "https://music.youtube.com/playlist?list=LM", None)
        assert ym_dir == self.temp_dir / "Liked Music"
        assert ym_dir.exists()
        
        # Regular playlist with info
        playlist_info = {
            "_type": "playlist",
            "playlist_title": "My Test Playlist"
        }
        playlist_dir = download.resolve_target_dir(self.temp_dir, "https://youtube.com/playlist?list=test", playlist_info)
        assert playlist_dir == self.temp_dir / "My Test Playlist"
        assert playlist_dir.exists()
        
        # Single video
        single_dir = download.resolve_target_dir(self.temp_dir, "https://youtube.com/watch?v=test", None)
        assert single_dir == self.temp_dir
        
        # Test clean_title with various inputs
        assert download.clean_title("Test Video: Part 1") != ""
        assert download.clean_title({"title": "Test Video"}) != ""
        assert download.clean_title(None) == "unknown"
        
        # Test expected_extensions
        assert ".mp3" in download.expected_extensions("mp3")
        assert ".opus" in download.expected_extensions("native")
        assert ".mp4" in download.expected_extensions("mp4")
    
    @patch('download.get_appdata_archive_path')
    def test_archive_manager_consistency(self, mock_path):
        """Test that ArchiveManager is consistent across operations."""
        mock_path.return_value = self.archive_file
        
        # Create first archive manager and add entries
        archive_mgr1 = download.ArchiveManager()
        
        # Create test file
        test_file = self.temp_dir / "test.mp3"
        test_file.touch()
        
        # Add entry
        archive_mgr1.add("test123", "youtube", "Test Video", test_file, "mp3")
        key = archive_mgr1.key("test123", "youtube", "mp3")
        
        # Verify key format
        assert key == "youtube_test123_mp3"
        assert key in archive_mgr1.data
        
        # Save and create new manager
        archive_mgr1.save()
        archive_mgr2 = download.ArchiveManager()
        
        # Verify consistency
        assert key in archive_mgr2.data
        assert archive_mgr2.data[key] == archive_mgr1.data[key]
        
        # Test finding
        found_entry = archive_mgr2.find("test123", "youtube", "mp3")
        assert found_entry is not None
        assert found_entry["title"] == "Test Video"
    
    def test_mp3_format_enforcement_integration(self):
        """Test that MP3 format enforcement works in real scenarios."""
        # Create source files with different extensions
        source_files = [
            self.temp_dir / "song.webm",
            self.temp_dir / "song.m4a", 
            self.temp_dir / "song.opus"
        ]
        
        for file in source_files:
            file.write_text("audio content")
        
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # Test copying each format to MP3 mode
        for source_file in source_files:
            archive_entry = {
                "file_path": str(source_file),
                "title": f"Test Song {source_file.suffix}"
            }
            
            result = download.optimized_copy_from_archive(archive_entry, target_dir, "mp3")
            assert result is True
            
            # Verify all files get .mp3 extension regardless of source
            title = download.clean_title(archive_entry['title'])
            target_file = target_dir / f"{title}.mp3"
            assert target_file.exists()
            assert target_file.suffix == ".mp3"
    
    def test_native_format_preservation_integration(self):
        """Test that native format preservation works correctly."""
        # Create source files with different extensions
        source_files = [
            self.temp_dir / "song.opus",
            self.temp_dir / "song.m4a",
            self.temp_dir / "song.aac"
        ]
        
        for file in source_files:
            file.write_text("audio content")
        
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # Test copying each format in native mode
        for source_file in source_files:
            archive_entry = {
                "file_path": str(source_file),
                "title": f"Test Song {source_file.suffix}"
            }
            
            result = download.optimized_copy_from_archive(archive_entry, target_dir, "native")
            assert result is True
            
            # Verify original extensions are preserved
            title = download.clean_title(archive_entry['title'])
            target_file = target_dir / f"{title}{source_file.suffix}"
            assert target_file.exists()
            assert target_file.suffix == source_file.suffix


class TestRegressionPrevention:
    """Tests to prevent regression of the bugs we fixed."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_mp3_copy_format_bug_fixed(self):
        """Regression test: MP3 mode should always use .mp3 extension."""
        # This was the original bug - MP3 mode would sometimes preserve non-MP3 extensions
        
        source_file = self.temp_dir / "audio.webm"
        source_file.write_text("webm audio content")
        
        archive_entry = {
            "file_path": str(source_file),
            "title": "Test Audio"
        }
        
        target_dir = self.temp_dir / "target"
        target_dir.mkdir()
        
        # This should ALWAYS create a .mp3 file, never .webm
        result = download.optimized_copy_from_archive(archive_entry, target_dir, "mp3")
        
        assert result is True
        
        # Verify .mp3 file was created (not .webm)
        mp3_file = target_dir / "Test Audio.mp3"
        webm_file = target_dir / "Test Audio.webm"
        
        assert mp3_file.exists()
        assert not webm_file.exists()
    
    def test_no_legacy_functions_remain(self):
        """Regression test: Ensure legacy functions are truly removed."""
        # These functions should no longer exist
        legacy_functions = [
            'load_archive',
            'save_archive', 
            'add_to_archive',
            'find_in_archive',
            'copy_from_archive',
            'build_archive_from_existing_files'
        ]
        
        for func_name in legacy_functions:
            assert not hasattr(download, func_name), f"Legacy function {func_name} still exists!"
    
    def test_archive_manager_single_source_of_truth(self):
        """Regression test: All archive operations should go through ArchiveManager."""
        # Verify that there's only one way to manage archives now
        
        # These should exist and work
        archive_mgr = download.ArchiveManager()
        assert hasattr(archive_mgr, 'data')
        assert hasattr(archive_mgr, 'save')
        assert hasattr(archive_mgr, 'add')
        assert hasattr(archive_mgr, 'find')
        assert hasattr(archive_mgr, 'key')
        
        # These optimized functions should exist
        assert hasattr(download, 'build_archive_from_existing_files_optimized')
        assert hasattr(download, 'optimized_copy_from_archive')
        
        # Helper functions should exist
        assert hasattr(download, 'resolve_target_dir')
        assert hasattr(download, 'clean_title')
        assert hasattr(download, 'expected_extensions')


if __name__ == "__main__":
    pytest.main([__file__])
