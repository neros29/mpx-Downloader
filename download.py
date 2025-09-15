"""
Interactive yt-dlp wrapper for Windows with colorized UI.

Features:
- Ask for URL(s) and MP3/MP4 mode.
- Smart playlist updates using a download archive (top-off only).
- Auto-use Firefox cookies for YouTube Music Liked Songs playlist.
- Sensible output folder defaults and Windows-safe filenames.

Note: Requires yt-dlp and ffmpeg. Colorized output uses colorama if available.
"""

from __future__ import annotations

import os
import json
import re
import sys
import shutil
import textwrap
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

try:
	from yt_dlp import YoutubeDL
	from yt_dlp.utils import sanitize_filename
except Exception as e:  # pragma: no cover
	print("[ERROR] yt-dlp is not installed. Please install it first:")
	print("  pip install -U yt-dlp")
	sys.exit(1)

# Optional: color support
try:
	from colorama import Fore, Style, init as colorama_init
	colorama_init(autoreset=True)
	C_OK = Fore.GREEN + Style.BRIGHT
	C_ERR = Fore.RED + Style.BRIGHT
	C_WARN = Fore.YELLOW + Style.BRIGHT
	C_HEAD = Fore.CYAN + Style.BRIGHT
	C_ASK = Fore.MAGENTA + Style.BRIGHT
	C_DIM = Style.DIM
	C_RESET = Style.RESET_ALL
except Exception:  # pragma: no cover
	# Fallback to no color
	class _NoColor:
		def __getattr__(self, _):
			return ""

	Fore = Style = _NoColor()
	C_OK = C_ERR = C_WARN = C_HEAD = C_ASK = C_DIM = C_RESET = ""


def banner() -> None:
	art = r"""
$$\      $$\ $$$$$$$\  $$\   $$\ 
$$$\    $$$ |$$  __$$\ $$ |  $$ |
$$$$\  $$$$ |$$ |  $$ |\$$\ $$  |
$$\$$\$$ $$ |$$$$$$$  | \$$$$  / 
$$ \$$$  $$ |$$  ____/  $$  $$<  
$$ |\$  /$$ |$$ |      $$  /\$$\ 
$$ | \_/ $$ |$$ |      $$ /  $$ |
\__|     \__|\__|      \__|  \__|
	"""
	print(C_HEAD + art + C_RESET)
	print(C_DIM + "Interactive yt-dlp wrapper — MP3/MP4, playlists, cookies, and more" + C_RESET)
	print()


def detect_ffmpeg() -> bool:
	exe = shutil.which("ffmpeg")
	return exe is not None


def is_youtube_music_liked(url: str) -> bool:
	u = url.lower()
	if "music.youtube.com" in u and ("list=lm" in u or "liked" in u):
		return True
	return False


def default_download_dir() -> Path:
	# Default to the directory where the program is run (current working directory)
	return Path.cwd()


def prompt(question: str, default: str | None = None) -> str:
	if default:
		q = f"{C_ASK}?{C_RESET} {question} {C_DIM}[{default}]{C_RESET}: "
	else:
		q = f"{C_ASK}?{C_RESET} {question}: "
	ans = input(q).strip()
	return ans or (default or "")


def choose_format() -> tuple[str, str]:
	print(C_ASK + "Select format:" + C_RESET)
	print(f"  {C_HEAD}[1]{C_RESET} MP3 (audio only)")
	print(f"  {C_HEAD}[2]{C_RESET} MKV (video, best seeking)")
	print(f"  {C_HEAD}[3]{C_RESET} MP4 (video, max compatibility)")
	while True:
		choice = prompt("Enter 1, 2, or 3", default="1")
		if choice == "1":
			return ("mp3", "mp3")
		elif choice == "2":
			return ("mkv", "video")
		elif choice == "3":
			return ("mp4", "video")
		print(C_WARN + "Please enter 1, 2, or 3." + C_RESET)


def split_urls(s: str) -> list[str]:
	# Allow space or newline separated multiple URLs
	parts = re.split(r"\s+", s.strip())
	return [p for p in parts if p]


def build_outtmpl(base_dir: Path, is_audio: bool) -> str:
	# Place downloads directly in the specified folder, not in subfolders
	out_root = base_dir
	try:
		out_root.mkdir(parents=True, exist_ok=True)
	except PermissionError:
		print(C_ERR + f"Permission denied: Cannot create directory {out_root}" + C_RESET)
		raise
	except Exception as e:
		print(C_WARN + f"Warning: Could not ensure directory exists: {e}" + C_RESET)
	# Download directly to the specified folder: <folder>/Title.mp3
	template = str(out_root / "%(title)s.%(ext)s")
	return template


def get_appdata_archive_path() -> Path:
	"""Get the path to the JSON archive file in AppData."""
	appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
	archive_dir = appdata / 'yt-dlp-wrapper'
	archive_dir.mkdir(parents=True, exist_ok=True)
	return archive_dir / 'download_archive.json'


def load_archive() -> dict:
	"""Load the download archive from AppData."""
	archive_path = get_appdata_archive_path()
	if not archive_path.exists():
		return {}
	
	try:
		with archive_path.open('r', encoding='utf-8') as f:
			return json.load(f)
	except Exception as e:
		print(C_WARN + f"Warning: Could not load archive: {e}" + C_RESET)
		return {}


def save_archive(archive: dict) -> None:
	"""Save the download archive to AppData."""
	try:
		archive_path = get_appdata_archive_path()
		with archive_path.open('w', encoding='utf-8') as f:
			json.dump(archive, f, indent=2, ensure_ascii=False)
	except Exception as e:
		print(C_WARN + f"Warning: Could not save archive: {e}" + C_RESET)


def add_to_archive(video_id: str, extractor: str, title: str, file_path: Path, container: str) -> None:
	"""Add a downloaded file to the archive with format differentiation."""
	archive = load_archive()
	# Include format in the key to differentiate MP3/MP4/MKV versions
	key = f"{extractor.lower()}_{video_id}_{container}"
	archive[key] = {
		'id': video_id,
		'extractor': extractor,
		'title': title,
		'format': container,
		'file_path': str(file_path.absolute()),
		'download_date': file_path.stat().st_mtime if file_path.exists() else 0.0
	}
	save_archive(archive)


def find_in_archive(video_id: str, extractor: str, container: str) -> dict | None:
	"""Find a video in the archive for the specific format and return its info if the file still exists."""
	archive = load_archive()
	key = f"{extractor.lower()}_{video_id}_{container}"
	
	if key in archive:
		entry = archive[key]
		file_path = Path(entry['file_path'])
		if file_path.exists() and file_path.stat().st_size > 0:
			return entry
		else:
			# File no longer exists, remove from archive
			del archive[key]
			save_archive(archive)
	
	return None


def copy_from_archive(archive_entry: dict, target_dir: Path, container: str) -> bool:
	"""Copy a file from archive location to target directory."""
	try:
		source_path = Path(archive_entry['file_path'])
		if not source_path.exists():
			return False
		
		# Determine target filename
		title = archive_entry['title']
		clean_title = sanitize_filename(title, restricted=False)
		
		# Determine extension based on format and source file
		if container == "mp3":
			target_ext = ".mp3"
		else:
			target_ext = source_path.suffix or f".{container}"
		
		target_path = target_dir / f"{clean_title}{target_ext}"
		
		# Avoid copying to the same location
		if source_path.resolve() == target_path.resolve():
			return True
		
		# Copy the file
		shutil.copy2(source_path, target_path)
		print(f"  📋 Copied from archive: {target_path.name}")
		return True
		
	except Exception as e:
		print(C_WARN + f"Warning: Could not copy from archive: {e}" + C_RESET)
		return False


def folder_name_from_info(info: dict) -> str:
	name = info.get("playlist_title") or info.get("uploader") or info.get("channel") or "Unknown"
	# Use yt-dlp's sanitizer to match file naming rules
	return sanitize_filename(str(name), restricted=False)


def check_existing_file(base_dir: Path, info: dict, container: str) -> bool:
	"""Check if a file already exists based on the video info and format."""
	try:
		title = info.get("title", "unknown")
		# Use yt-dlp's sanitizer to match the actual filename that would be created
		clean_title = sanitize_filename(title, restricted=False)
		
		# Determine the expected extension
		if container == "mp3":
			extensions = [".mp3"]
		else:
			extensions = [".mp4", ".m4v", ".mkv", ".webm", ".avi"]  # Common video formats
		
		# Check for existing files with any of the possible extensions
		for ext in extensions:
			potential_file = base_dir / f"{clean_title}{ext}"
			if potential_file.exists() and potential_file.stat().st_size > 0:
				return True
		return False
	except Exception:
		return False


def download_progress_hook(d: dict, base_dir: Path, container: str) -> None:
	"""Progress hook to provide real-time download feedback."""
	if d['status'] == 'downloading':
		if 'total_bytes' in d and 'downloaded_bytes' in d:
			percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
			speed = d.get('speed', 0)
			if speed:
				speed_str = f" at {speed/1024/1024:.1f}MB/s"
			else:
				speed_str = ""
			print(f"\r  📥 {percent:.1f}% downloaded{speed_str}", end='', flush=True)
	elif d['status'] == 'finished':
		print(f"\r  ✅ Downloaded: {Path(d['filename']).name}")
	elif d['status'] == 'error':
		print(f"\r  ❌ Error downloading: {d.get('filename', 'unknown')}")


def should_download_hook(info: dict, base_dir: Path, container: str) -> bool:
	"""Hook to determine if a video should be downloaded based on existing files."""
	if check_existing_file(base_dir, info, container):
		title = info.get("title", "unknown")
		print(f"  ⏭️  Skipping (already exists): {title}")
		return False
	return True


def _stable_key_for_path(abs_path: str, fmt: str) -> str:
	"""Generate a stable hash-based key for a file path to avoid collisions."""
	h = hashlib.blake2b(abs_path.encode('utf-8'), digest_size=8).hexdigest()
	return f"local_{h}_{fmt}"


def build_archive_from_existing_files(download_dir: Path, container: str) -> None:
	"""Build archive from existing files in the download directory."""
	try:
		archive = load_archive()
		# Determine extensions based on format
		if container == "mp3":
			extensions = ['.mp3']
		else:
			extensions = ['.mp4', '.mkv', '.webm', '.avi']
		
		for file_path in download_dir.glob("*"):
			if file_path.is_file() and file_path.suffix.lower() in extensions:
				# Generate a stable key for existing files (without video ID)
				key = _stable_key_for_path(str(file_path.absolute()), container)
				
				if key not in archive:
					archive[key] = {
						'id': file_path.stem,
						'extractor': 'local',
						'title': file_path.stem,
						'format': container,
						'file_path': str(file_path.absolute()),
						'download_date': file_path.stat().st_mtime
					}
		save_archive(archive)
	except Exception as e:
		print(C_WARN + f"Warning: Could not build archive from existing files: {e}" + C_RESET)


def generate_m3u_for_playlist(info: dict, download_dir: Path, container: str) -> None:
	"""Generate an .m3u file with original playlist order, including existing and newly downloaded tracks."""
	entries = info.get("entries") or []
	if not entries:
		return
	ext = "mp3" if container == "mp3" else container

	lines: list[str] = []
	for entry in entries:
		if not entry:
			continue
		title = entry.get("title") or "unknown"
		fname = sanitize_filename(title, restricted=False) + f".{ext}"
		fpath = download_dir / fname
		if fpath.exists():
			# Write relative path for portability
			lines.append(fname)

	if not lines:
		return

	m3u_name_source = info.get("playlist_title") or folder_name_from_info(info)
	m3u_name = sanitize_filename(str(m3u_name_source), restricted=False) + ".m3u"
	try:
		with (download_dir / m3u_name).open("w", encoding="utf-8") as f:
			for line in lines:
				f.write(line + "\r\n")
	except Exception:
		pass


class SmartYoutubeDL(YoutubeDL):
	"""Custom YoutubeDL class that uses JSON archive and copies existing files."""
	
	def __init__(self, params=None, base_dir=None, container=None):
		super().__init__(params)
		self.base_dir = base_dir
		self.container = container
		self.skipped_count = 0
		self.downloaded_count = 0
		self.copied_count = 0
	
	def process_info(self, info_dict):
		"""Override to add archive checking and copy logic."""
		# Check if this is a single video entry (not a playlist)
		if info_dict.get('_type') != 'playlist' and self.base_dir and self.container:
			video_id = info_dict.get('id')
			extractor = info_dict.get('extractor_key', info_dict.get('extractor', 'generic'))
			
			if video_id and extractor:
				# Check if we have this in our archive for the specific format
				archive_entry = find_in_archive(video_id, extractor, self.container)
				if archive_entry:
					# Try to copy from archive
					if copy_from_archive(archive_entry, self.base_dir, self.container):
						self.copied_count += 1
						return None  # Skip downloading
				
				# Check if file already exists in current directory
				if check_existing_file(self.base_dir, info_dict, self.container):
					title = info_dict.get("title", "unknown")
					print(f"  ⏭️  Skipping (already exists): {title}")
					self.skipped_count += 1
					return None  # Skip this video
		
		# Process normally (download)
		result = super().process_info(info_dict)
		
		# If download was successful, add to archive
		if result and info_dict.get('_type') != 'playlist':
			self.downloaded_count += 1
			self._add_successful_download_to_archive(info_dict)
		
		return result
	
	def _add_successful_download_to_archive(self, info_dict):
		"""Add a successfully downloaded file to the archive."""
		try:
			video_id = info_dict.get('id')
			extractor = info_dict.get('extractor_key', info_dict.get('extractor', 'generic'))
			title = info_dict.get('title', 'unknown')
			
			if video_id and extractor and self.container and self.base_dir:
				# Determine the expected file path
				clean_title = sanitize_filename(title, restricted=False)
				if self.container == "mp3":
					ext = ".mp3"
				else:
					ext = f".{self.container}"  # .mkv or .mp4
				
				file_path = self.base_dir / f"{clean_title}{ext}"
				if file_path.exists():
					add_to_archive(video_id, extractor, title, file_path, self.container)
		except Exception as e:
			print(C_DIM + f"Note: Could not add to archive: {e}" + C_RESET)


def ydl_opts_common(base_dir: Path, container: str, fmt_type: str, use_firefox_cookies: bool) -> dict:
	is_audio = fmt_type == "audio"
	opts: dict = {
		"outtmpl": build_outtmpl(base_dir, is_audio),
		"restrictfilenames": False,
		"windowsfilenames": True,
		"noprogress": False,
		"ignoreerrors": True,
		"retries": 10,
		"fragment_retries": 10,
		"concurrent_fragment_downloads": 5,
		"continuedl": True,
		"writeinfojson": False,  # Disable individual JSON files
		"writethumbnail": True,
		"overwrites": False,
		"extract_flat": False,  # Don't extract flat for efficient playlist processing
		"progress_hooks": [lambda d: download_progress_hook(d, base_dir, container)],
		"postprocessor_args": [
			"-metadata", "comment=Downloaded with yt-dlp wrapper",
			# VLC-friendly options to fix fast-forward issues
			"-avoid_negative_ts", "make_zero",
			"-fflags", "+discardcorrupt",
		],
	}

	if is_audio:
		opts.update(
			{
				"format": "bestaudio/best",
				"postprocessors": [
					{
						"key": "FFmpegExtractAudio",
						"preferredcodec": "mp3",
						"preferredquality": "0",
					},
					{"key": "EmbedThumbnail"},
					{"key": "FFmpegMetadata"},
				],
				"prefer_ffmpeg": True,
				"keepvideo": False,
			}
		)
	else:
		# Video settings optimized for container type
		video_postprocessors = [
			{"key": "FFmpegMetadata"},
		]
		
		if container == "mkv":
			# MKV: Better seeking, can embed thumbnails reliably
			opts.update({
				"format": "bestvideo+bestaudio/best",
				"merge_output_format": "mkv",
				"remux_video": "mkv",  # Also remux single-stream downloads
			})
			video_postprocessors.append({"key": "EmbedThumbnail"})
			# Add faststart equivalent for MKV seeking
			opts["postprocessor_args"].extend(["-movflags", "+faststart"])
		else:
			# MP4: Max compatibility, but more finicky seeking
			opts.update({
				"format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo*+bestaudio/best",
				"merge_output_format": "mp4",
				"remux_video": "mp4",
			})
			# Extra MP4 seeking fixes
			opts["postprocessor_args"].extend([
				"-movflags", "+faststart",
				"-fflags", "+genpts",  # Generate presentation timestamps
			])
		
		video_postprocessors.append({
			"key": "FFmpegVideoConvertor",
			"preferedformat": container,
		})
		
		opts.update({
			"postprocessors": video_postprocessors,
			"prefer_ffmpeg": True,
		})

	if use_firefox_cookies:
		opts["cookiesfrombrowser"] = ("firefox", None, None, None)

	return opts


def download_urls(urls: list[str], base_dir: Path, container: str, fmt_type: str, force_firefox_cookies: bool) -> int:
	# Build options
	try:
		opts = ydl_opts_common(base_dir, container, fmt_type, force_firefox_cookies)
	except Exception as e:
		print(C_ERR + f"Error setting up download options: {e}" + C_RESET)
		return 0
	
	# Build archive from existing files in the download directory
	try:
		build_archive_from_existing_files(base_dir, container)
	except Exception as e:
		print(C_WARN + f"Warning: Could not build archive from existing files: {e}" + C_RESET)

	total_ok = 0
	# Use our custom YoutubeDL class that uses JSON archive and copies files
	with SmartYoutubeDL(opts, base_dir, container) as ydl:
		for url in urls:
			print(C_HEAD + f"\n➡ Processing: {url}" + C_RESET)
			try:
				# Auto-use cookies if it's a YT Music Liked URL
				if not force_firefox_cookies and is_youtube_music_liked(url):
					print(C_WARN + "Auto-enabling Firefox cookies for Liked Music." + C_RESET)
					ydl.params["cookiesfrombrowser"] = ("firefox", None, None, None)
				
				# Reset counters for this URL
				ydl.skipped_count = 0
				ydl.downloaded_count = 0
				ydl.copied_count = 0
				
				# Download with smart archive checking and copying
				res = ydl.download([url])
				
				# Report results
				if ydl.downloaded_count > 0:
					print(C_OK + f"✓ Downloaded {ydl.downloaded_count} new file(s)" + C_RESET)
				if ydl.copied_count > 0:
					print(C_OK + f"📋 Copied {ydl.copied_count} file(s) from archive" + C_RESET)
				if ydl.skipped_count > 0:
					print(C_DIM + f"⏭️  Skipped {ydl.skipped_count} existing file(s)" + C_RESET)
				
				# ydl.download returns 0 on success
				if res == 0:
					total_ok += 1
				else:
					print(C_WARN + f"⚠ Download completed with warnings for: {url}" + C_RESET)
					
				# Only extract info for M3U generation if needed (for playlists)
				try:
					info = ydl.extract_info(url, download=False)
					if isinstance(info, dict) and (info.get("_type") == "playlist" or info.get("entries")):
						generate_m3u_for_playlist(info, base_dir, container)
						print(C_DIM + "Generated M3U playlist file" + C_RESET)
				except Exception as e:
					print(C_DIM + f"Note: Could not generate M3U file: {e}" + C_RESET)
					
			except KeyboardInterrupt:
				print(C_WARN + "\nDownload interrupted by user" + C_RESET)
				raise
			except Exception as e:
				print(C_ERR + f"✗ Error downloading {url}: {e}" + C_RESET)
				# Continue with other URLs even if one fails
				continue
	return total_ok


def show_help() -> None:
	"""Display help information and exit."""
	help_text = f"""
{C_HEAD}Interactive yt-dlp wrapper — MP3/MKV/MP4, playlists, cookies, and more{C_RESET}

{C_HEAD}USAGE:{C_RESET}
  python download.py [OPTIONS] [URLs...]

{C_HEAD}OPTIONS:{C_RESET}
  {C_ASK}--help{C_RESET}                    Show this help message and exit
  {C_ASK}--format{C_RESET} FORMAT           Download format: mp3, mkv, mp4 (default: interactive)
  {C_ASK}--outdir{C_RESET} PATH             Output directory (default: current directory)
  {C_ASK}--firefox-cookies{C_RESET}         Use Firefox cookies for authentication
  {C_ASK}--file{C_RESET} FILE               Read URLs from text file (one per line)
  {C_ASK}--load{C_RESET} DIRECTORY          Scan directory and add existing files to archive
  {C_ASK}--show-archive{C_RESET}            Display archive information
  {C_ASK}--backup{C_RESET}                  Create backup of download archive
  {C_ASK}--clear{C_RESET} [OPTIONS]         Clear archive entries:
                            all              - Clear entire archive
                            NAME             - Clear entries matching name
                            DATE [DATE]      - Clear entries in date range

{C_HEAD}FORMATS:{C_RESET}
  {C_ASK}mp3{C_RESET}     Audio only (MP3 with embedded thumbnails)
  {C_ASK}mkv{C_RESET}     Video in MKV container (best seeking, embedded thumbnails)
  {C_ASK}mp4{C_RESET}     Video in MP4 container (maximum compatibility)

{C_HEAD}EXAMPLES:{C_RESET}
  {C_DIM}# Interactive mode{C_RESET}
  python download.py

  {C_DIM}# Download audio only{C_RESET}
  python download.py --format mp3 "https://youtube.com/watch?v=..."

  {C_DIM}# Download video with best seeking (MKV){C_RESET}
  python download.py --format mkv --outdir ./music "https://youtube.com/playlist?list=..."

  {C_DIM}# Use Firefox cookies for private playlists{C_RESET}
  python download.py --firefox-cookies --format mp3 "https://music.youtube.com/playlist?list=LM"

  {C_DIM}# Load URLs from file{C_RESET}
  python download.py --file urls.txt --format mkv

  {C_DIM}# Add existing files to archive{C_RESET}
  python download.py --load ./my_music_folder

  {C_DIM}# Archive management{C_RESET}
  python download.py --show-archive
  python download.py --backup
  python download.py --clear "Rick Astley"
  python download.py --clear "2024-01-01" "2024-12-31"

{C_HEAD}FEATURES:{C_RESET}
  • Smart archive system prevents re-downloading existing files
  • Automatic Firefox cookie detection for YouTube Music Liked Songs
  • Copy files from archive instead of re-downloading when possible
  • Generate M3U playlists for downloaded content
  • Windows-safe filenames and robust error handling
  • VLC-optimized seeking for video files (especially MKV)

{C_HEAD}ARCHIVE:{C_RESET}
  Archive location: {C_DIM}{get_appdata_archive_path()}{C_RESET}
"""
	print(help_text)


def parse_args(argv: list[str]) -> dict:
	# Lightweight arg parsing to allow non-interactive usage via download.bat
	# Supported:
	#   --help                    (show help and exit)
	#   --format mp3|mkv|mp4
	#   --outdir <path>
	#   --firefox-cookies
	#   --load <directory>        (scan directory and add files to archive)
	#   --file <file>             (load URLs from text file)
	#   --show-archive
	#   --backup                  (backup archive)
	#   --clear [all|<name>|<from_date> [to_date]]
	#   <urls...>
	args = {
		"help": False,
		"format": None,
		"outdir": None,
		"firefox_cookies": False,
		"load_directory": None,
		"file_path": None,
		"show_archive": False,
		"backup": False,
		"clear": [],
		"urls": [],
	}
	
	i = 0
	n = len(argv)
	while i < n:
		tok = argv[i]
		if tok in ("--help", "-h"):
			args["help"] = True
			i += 1
		elif tok == "--format" and i + 1 < n:
			args["format"] = argv[i + 1]
			i += 2
		elif tok == "--outdir" and i + 1 < n:
			args["outdir"] = argv[i + 1]
			i += 2
		elif tok == "--firefox-cookies":
			args["firefox_cookies"] = True
			i += 1
		elif tok == "--load" and i + 1 < n:
			args["load_directory"] = argv[i + 1]
			i += 2
		elif tok == "--file" and i + 1 < n:
			args["file_path"] = argv[i + 1]
			i += 2
		elif tok == "--show-archive":
			args["show_archive"] = True
			i += 1
		elif tok == "--backup":
			args["backup"] = True
			i += 1
		elif tok == "--clear":
			i += 1
			clear_args = []
			while i < n and not argv[i].startswith("--"):
				clear_args.append(argv[i])
				i += 1
			args["clear"] = clear_args
			# Continue processing from current position (i)
		elif tok.startswith("-"):
			# ignore unknown switches for simplicity
			i += 1
		else:
			args["urls"].append(tok)
			i += 1
	return args


def backup_archive() -> bool:
	"""Create a backup of the current archive."""
	try:
		archive_path = get_appdata_archive_path()
		if not archive_path.exists():
			print(C_WARN + "No archive file found to backup." + C_RESET)
			return False
		
		backup_path = archive_path.parent / "download_archive_backup.json"
		shutil.copy2(archive_path, backup_path)
		
		print(C_OK + f"✓ Archive backed up to: {backup_path}" + C_RESET)
		return True
	except Exception as e:
		print(C_ERR + f"Error creating backup: {e}" + C_RESET)
		return False


def clear_archive_by_name(search_term: str) -> int:
	"""Clear archive entries that match a search term in the title."""
	try:
		archive = load_archive()
		if not archive:
			print(C_WARN + "Archive is empty." + C_RESET)
			return 0
		
		# Find matching entries
		matches = []
		for key, entry in archive.items():
			title = entry.get('title', '').lower()
			if search_term.lower() in title:
				matches.append((key, entry))
		
		if not matches:
			print(C_WARN + f"No entries found matching '{search_term}'." + C_RESET)
			return 0
		
		# Show matches and confirm
		print(C_HEAD + f"Found {len(matches)} matching entries:" + C_RESET)
		for i, (key, entry) in enumerate(matches[:10], 1):  # Show first 10
			title = entry.get('title', 'Unknown')
			fmt = entry.get('format', 'unknown')
			print(f"  {i}. {title} ({fmt})")
		
		if len(matches) > 10:
			print(C_DIM + f"  ... and {len(matches) - 10} more" + C_RESET)
		
		confirm = prompt(f"Delete these {len(matches)} entries? (y/n)", "n").lower()
		if confirm not in ("y", "yes"):
			print(C_WARN + "Cancelled." + C_RESET)
			return 0
		
		# Remove matches
		for key, _ in matches:
			del archive[key]
		
		save_archive(archive)
		print(C_OK + f"✓ Removed {len(matches)} entries from archive" + C_RESET)
		return len(matches)
		
	except Exception as e:
		print(C_ERR + f"Error clearing by name: {e}" + C_RESET)
		return 0


def parse_date_input(date_str: str) -> datetime | None:
	"""Parse various date formats into datetime object."""
	try:
		# Try different date formats
		formats = [
			"%Y-%m-%d",           # 2023-12-25
			"%Y/%m/%d",           # 2023/12/25
			"%m/%d/%Y",           # 12/25/2023
			"%d/%m/%Y",           # 25/12/2023
			"%Y-%m-%d %H:%M",     # 2023-12-25 14:30
			"%Y-%m-%d %H:%M:%S",  # 2023-12-25 14:30:45
		]
		
		for fmt in formats:
			try:
				return datetime.strptime(date_str, fmt)
			except ValueError:
				continue
		
		# Try relative dates
		date_str_lower = date_str.lower()
		now = datetime.now()
		
		if "today" in date_str_lower:
			return now.replace(hour=0, minute=0, second=0, microsecond=0)
		elif "yesterday" in date_str_lower:
			return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
		elif "week" in date_str_lower:
			return now - timedelta(weeks=1)
		elif "month" in date_str_lower:
			return now - timedelta(days=30)
		
		return None
	except Exception:
		return None


def clear_archive_by_date(from_date_str: str, to_date_str: str | None = None) -> int:
	"""Clear archive entries within a date range."""
	try:
		archive = load_archive()
		if not archive:
			print(C_WARN + "Archive is empty." + C_RESET)
			return 0
		
		from_date = parse_date_input(from_date_str)
		if not from_date:
			print(C_ERR + f"Invalid date format: {from_date_str}" + C_RESET)
			print(C_DIM + "Try formats like: 2023-12-25, 12/25/2023, 'last week', 'last month'" + C_RESET)
			return 0
		
		to_date = None
		if to_date_str:
			to_date = parse_date_input(to_date_str)
			if not to_date:
				print(C_ERR + f"Invalid date format: {to_date_str}" + C_RESET)
				return 0
		else:
			to_date = datetime.now()
		
		# Find matching entries
		matches = []
		for key, entry in archive.items():
			try:
				download_date = float(entry.get('download_date', 0))
				entry_date = datetime.fromtimestamp(download_date)
				
				if from_date <= entry_date <= to_date:
					matches.append((key, entry, entry_date))
			except (ValueError, TypeError, OSError):
				continue
		
		if not matches:
			print(C_WARN + f"No entries found between {from_date.strftime('%Y-%m-%d')} and {to_date.strftime('%Y-%m-%d')}." + C_RESET)
			return 0
		
		# Show matches and confirm
		print(C_HEAD + f"Found {len(matches)} entries between {from_date.strftime('%Y-%m-%d')} and {to_date.strftime('%Y-%m-%d')}:" + C_RESET)
		for i, (key, entry, entry_date) in enumerate(matches[:10], 1):  # Show first 10
			title = entry.get('title', 'Unknown')
			fmt = entry.get('format', 'unknown')
			date_str = entry_date.strftime('%Y-%m-%d')
			print(f"  {i}. {title} ({fmt}) - {date_str}")
		
		if len(matches) > 10:
			print(C_DIM + f"  ... and {len(matches) - 10} more" + C_RESET)
		
		confirm = prompt(f"Delete these {len(matches)} entries? (y/n)", "n").lower()
		if confirm not in ("y", "yes"):
			print(C_WARN + "Cancelled." + C_RESET)
			return 0
		
		# Remove matches
		for key, _, _ in matches:
			del archive[key]
		
		save_archive(archive)
		print(C_OK + f"✓ Removed {len(matches)} entries from archive" + C_RESET)
		return len(matches)
		
	except Exception as e:
		print(C_ERR + f"Error clearing by date: {e}" + C_RESET)
		return 0


def clear_entire_archive() -> bool:
	"""Clear the entire archive with confirmation."""
	try:
		archive = load_archive()
		if not archive:
			print(C_WARN + "Archive is already empty." + C_RESET)
			return True
		
		count = len(archive)
		print(C_WARN + f"⚠️  WARNING: This will delete ALL {count} entries from the archive!" + C_RESET)
		print(C_DIM + "This action cannot be undone unless you have a backup." + C_RESET)
		
		confirm1 = prompt("Are you sure you want to clear the entire archive? (yes/no)", "no").lower()
		if confirm1 != "yes":
			print(C_WARN + "Cancelled." + C_RESET)
			return False
		
		confirm2 = prompt("Type 'DELETE ALL' to confirm", "").upper()
		if confirm2 != "DELETE ALL":
			print(C_WARN + "Cancelled - confirmation text doesn't match." + C_RESET)
			return False
		
		# Clear the archive
		save_archive({})
		print(C_OK + f"✓ Cleared entire archive ({count} entries removed)" + C_RESET)
		return True
		
	except Exception as e:
		print(C_ERR + f"Error clearing archive: {e}" + C_RESET)
		return False


def interactive_clear() -> int:
	"""Interactive archive clearing menu."""
	print(C_HEAD + "Archive Clearing Options:" + C_RESET)
	print("  [1] Clear by name/title")
	print("  [2] Clear by date range")
	print("  [3] Clear all (dangerous!)")
	print("  [4] Cancel")
	
	choice = prompt("Select option (1-4)", "4")
	
	if choice == "1":
		search_term = prompt("Enter name/title to search for")
		if search_term:
			return clear_archive_by_name(search_term)
	elif choice == "2":
		from_date = prompt("From date (YYYY-MM-DD or 'last week', 'last month')")
		to_date = prompt("To date (YYYY-MM-DD or leave empty for today)", "")
		if from_date:
			return clear_archive_by_date(from_date, to_date if to_date else None)
	elif choice == "3":
		if clear_entire_archive():
			return -1  # Special return for full clear
	
	print(C_WARN + "Cancelled." + C_RESET)
	return 0


def show_archive_info() -> None:
	"""Display information about the archive."""
	archive = load_archive()
	archive_path = get_appdata_archive_path()
	
	print(C_HEAD + "Archive Information:" + C_RESET)
	print(f"  Location: {C_DIM}{archive_path}{C_RESET}")
	print(f"  Total entries: {C_DIM}{len(archive)}{C_RESET}")
	
	if archive:
		mp3_count = sum(1 for entry in archive.values() if entry.get('format') == 'mp3')
		mp4_count = sum(1 for entry in archive.values() if entry.get('format') == 'mp4')
		local_count = sum(1 for entry in archive.values() if entry.get('extractor') == 'local')
		
		print(f"  MP3 files: {C_DIM}{mp3_count}{C_RESET}")
		print(f"  MP4 files: {C_DIM}{mp4_count}{C_RESET}")
		print(f"  Local files: {C_DIM}{local_count}{C_RESET}")


def load_urls_from_file(file_path: str) -> list[str]:
	"""Load URLs from a text file, one per line."""
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			urls = []
			for line_num, line in enumerate(f, 1):
				line = line.strip()
				if line and not line.startswith('#'):  # Skip empty lines and comments
					if line.startswith(('http://', 'https://')):
						urls.append(line)
					else:
						print(C_WARN + f"Line {line_num}: '{line}' doesn't look like a valid URL" + C_RESET)
			return urls
	except FileNotFoundError:
		print(C_ERR + f"File not found: {file_path}" + C_RESET)
		return []
	except Exception as e:
		print(C_ERR + f"Error reading file {file_path}: {e}" + C_RESET)
		return []


def load_directory_to_archive(directory_path: str) -> bool:
	"""Scan a directory and add all MP3/MP4 files to the archive."""
	try:
		dir_path = Path(directory_path)
		if not dir_path.exists():
			print(C_ERR + f"Directory not found: {directory_path}" + C_RESET)
			return False
		
		if not dir_path.is_dir():
			print(C_ERR + f"Path is not a directory: {directory_path}" + C_RESET)
			return False
		
		print(C_HEAD + f"Scanning directory: {dir_path}" + C_RESET)
		
		# Supported file extensions
		audio_extensions = ['.mp3', '.m4a', '.aac', '.flac', '.wav']
		video_extensions = ['.mp4', '.mkv', '.webm', '.avi', '.mov']
		all_extensions = audio_extensions + video_extensions
		
		archive = load_archive()
		added_count = 0
		
		# Recursively scan directory
		for file_path in dir_path.rglob('*'):
			if file_path.is_file() and file_path.suffix.lower() in all_extensions:
				# Determine format based on extension
				if file_path.suffix.lower() in audio_extensions:
					container = 'mp3'
				else:
					# Default to mkv for video files (better seeking)
					container = 'mkv'
				
				# Generate a stable key based on absolute path and format
				abs_path = str(file_path.absolute())
				key = _stable_key_for_path(abs_path, container)
				
				# Check if this exact file path is already in archive (prevent duplicates)
				already_exists = any(
					entry.get('file_path') == abs_path and entry.get('format') == container
					for entry in archive.values()
				)
				
				if not already_exists:
					archive[key] = {
						'id': file_path.stem,
						'extractor': 'local',
						'title': file_path.stem,
						'format': container,
						'file_path': abs_path,
						'download_date': file_path.stat().st_mtime
					}
					added_count += 1
					print(f"  📁 Added: {file_path.name}")
				else:
					print(f"  ⏭️  Already in archive: {file_path.name}")
		
		# Save the updated archive
		save_archive(archive)
		
		print(C_OK + f"✓ Added {added_count} new files to archive" + C_RESET)
		if added_count == 0:
			print(C_DIM + "  (All files were already in archive)" + C_RESET)
		
		return True
		
	except Exception as e:
		print(C_ERR + f"Error scanning directory: {e}" + C_RESET)
		return False


def main() -> int:
	banner()

	if not detect_ffmpeg():
		print(C_WARN + "ffmpeg not found. Conversions, merges, and thumbnails may fail." + C_RESET)
		print(C_DIM + "Install from https://ffmpeg.org/download.html or winget: winget install Gyan.FFmpeg" + C_RESET)

	args = parse_args(sys.argv[1:])

	# Handle help first
	if args["help"]:
		show_help()
		return 0

	# Handle special commands
	if args["backup"]:
		backup_archive()
		return 0
	
	if args["show_archive"]:
		show_archive_info()
		return 0
	
	if args["clear"]:
		clear_args = args["clear"]
		
		if not clear_args:
			# Interactive mode
			result = interactive_clear()
			return 0 if result >= 0 else 0
		elif len(clear_args) == 1:
			if clear_args[0].lower() == "all":
				# Clear all
				clear_entire_archive()
				return 0
			else:
				# Clear by name
				clear_archive_by_name(clear_args[0])
				return 0
		elif len(clear_args) == 2:
			# Clear by date range
			clear_archive_by_date(clear_args[0], clear_args[1])
			return 0
		else:
			print(C_ERR + "Invalid --clear arguments. Use: --clear [all|<name>|<from_date> [to_date]]" + C_RESET)
			return 1

	# Collect URL(s)
	urls: list[str]
	if args["urls"]:
		urls = args["urls"]
	elif args["load_directory"]:
		# Directory mode - scan and add files to archive
		print(C_HEAD + f"Directory mode: Adding files from {args['load_directory']} to archive" + C_RESET)
		success = load_directory_to_archive(args["load_directory"])
		if success:
			print(C_OK + "Directory scan completed successfully!" + C_RESET)
			return 0
		else:
			print(C_ERR + "Directory scan failed!" + C_RESET)
			return 1
	elif args["file_path"]:
		# File mode - load URLs from text file
		print(C_HEAD + f"File mode: Loading URLs from {args['file_path']}" + C_RESET)
		urls = load_urls_from_file(args["file_path"])
		if not urls:
			print(C_ERR + "No valid URLs found in file." + C_RESET)
			return 1
		print(C_OK + f"Loaded {len(urls)} URL(s) from file" + C_RESET)
	else:
		entered = prompt("Enter video/playlist URL(s) (space or newline separated)")
		urls = split_urls(entered)
		while not urls:
			print(C_WARN + "Please enter at least one URL." + C_RESET)
			entered = prompt("Enter video/playlist URL(s)")
			urls = split_urls(entered)

	# Validate URLs
	for url in urls:
		if not url.startswith(('http://', 'https://')):
			print(C_WARN + f"Warning: '{url}' doesn't look like a valid URL" + C_RESET)

	# Format
	try:
		if args["format"]:
			# Handle command line format argument
			if args["format"] == "mp3":
				container, fmt_type = ("mp3", "audio")
			elif args["format"] == "mkv":
				container, fmt_type = ("mkv", "video")
			elif args["format"] == "mp4":
				container, fmt_type = ("mp4", "video")
			else:
				print(C_ERR + f"Invalid format: {args['format']}. Using MP3 as default." + C_RESET)
				container, fmt_type = ("mp3", "audio")
		else:
			container, fmt_type = choose_format()
	except Exception as e:
		print(C_ERR + f"Error selecting format: {e}. Using MP3 as default." + C_RESET)
		container, fmt_type = ("mp3", "audio")

	# Output directory
	default_dir = default_download_dir()
	outdir_str = args["outdir"] or prompt("Output folder", str(default_dir))
	
	try:
		base_dir = Path(outdir_str).expanduser().resolve()
		# Test if we can create the directory
		base_dir.mkdir(parents=True, exist_ok=True)
		
		# Test if we can write to the directory
		test_file = base_dir / ".write_test"
		try:
			test_file.touch()
			test_file.unlink()
		except Exception:
			raise PermissionError(f"Cannot write to directory: {base_dir}")
			
	except PermissionError as e:
		print(C_ERR + f"Permission Error: {e}" + C_RESET)
		print(C_WARN + "Try one of these solutions:" + C_RESET)
		print(f"  1. Use a different folder (e.g., {Path.home() / 'Downloads'})")
		print("  2. Run as administrator")
		print("  3. Choose a folder you have write access to")
		return 1
	except Exception as e:
		print(C_ERR + f"Error creating output directory: {e}" + C_RESET)
		print(C_WARN + f"Failed to create: {outdir_str}" + C_RESET)
		print(C_DIM + f"Resolved to: {Path(outdir_str).expanduser().resolve()}" + C_RESET)
		return 1

	# Firefox cookies preference
	try:
		use_firefox_cookies = args["firefox_cookies"]
		# If any URL matches liked music, auto-enable regardless of toggle
		if any(is_youtube_music_liked(u) for u in urls):
			use_firefox_cookies = True
			print(C_WARN + "Detected YouTube Music Liked playlist; Firefox cookies will be used." + C_RESET)
	except Exception as e:
		print(C_WARN + f"Warning: Could not check for YouTube Music URLs: {e}" + C_RESET)
		use_firefox_cookies = args["firefox_cookies"]

	# Summary
	print()
	print(C_HEAD + "Summary:" + C_RESET)
	print("  URLs:      " + C_DIM + ", ".join(urls) + C_RESET)
	print("  Format:    " + C_DIM + container.upper() + C_RESET)
	print("  Output to: " + C_DIM + str(base_dir) + C_RESET)
	if use_firefox_cookies:
		print("  Cookies:   " + C_DIM + "Firefox (cookies-from-browser)" + C_RESET)
	print()

	# Confirm
	try:
		confirm = prompt("Proceed? (y/n)", "y").lower()
		if confirm not in ("y", "yes"):
			print(C_WARN + "Canceled by user." + C_RESET)
			return 0
	except KeyboardInterrupt:
		print(C_WARN + "\nCanceled by user." + C_RESET)
		return 0
	except Exception as e:
		print(C_ERR + f"Error getting confirmation: {e}" + C_RESET)
		return 1

	# Download
	try:
		ok = download_urls(urls, base_dir, container, fmt_type, use_firefox_cookies)
	except KeyboardInterrupt:
		print(C_WARN + "\nDownload interrupted by user." + C_RESET)
		return 130
	except Exception as e:
		print(C_ERR + f"Fatal error during download: {e}" + C_RESET)
		return 1

	print()
	if ok:
		print(C_OK + f"Done. {ok} item(s) processed without fatal errors." + C_RESET)
		print(C_DIM + f"Archive file: {get_appdata_archive_path()}" + C_RESET)
	else:
		print(C_ERR + "No items were downloaded (check errors above)." + C_RESET)
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except KeyboardInterrupt:
		print("\n" + C_WARN + "Interrupted." + C_RESET)
		raise SystemExit(130)
