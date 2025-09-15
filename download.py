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


def get_appdata_archive_path() -> Path:
	"""Get the path to the JSON archive file in platform-appropriate directory."""
	if os.name == 'nt':  # Windows
		appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
		archive_dir = appdata / 'yt-dlp-wrapper'
	else:  # Linux/macOS
		# Use XDG Base Directory specification
		xdg_data_home = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
		archive_dir = Path(xdg_data_home) / 'yt-dlp-wrapper'
	
	archive_dir.mkdir(parents=True, exist_ok=True)
	return archive_dir / 'download_archive.json'


class ArchiveManager:
	"""Cached archive manager to avoid per-item JSON reads/writes."""
	
	def __init__(self):
		self._path = get_appdata_archive_path()
		try:
			self.data = json.loads(self._path.read_text(encoding="utf-8"))
		except Exception:
			self.data = {}
		self._dirty = False
	
	def save(self):
		"""Save the archive if it has been modified."""
		if self._dirty:
			try:
				self._path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
				self._dirty = False
			except Exception as e:
				print(f"    {C_WARN}Warning: Could not save archive: {e}{C_RESET}")
	
	def key(self, vid: str, extractor: str, container: str) -> str:
		"""Generate a consistent key for archive entries."""
		return f"{(extractor or 'generic').lower()}_{vid}_{container}"
	
	def find(self, vid: str, extractor: str, container: str, title: str | None = None) -> dict | None:
		"""Find a video in the archive, with title fallback if no exact match."""
		k = self.key(vid, extractor, container)
		
		# First try exact key match
		if k in self.data:
			p = Path(self.data[k]["file_path"])
			if p.exists():
				return self.data[k]
			# File no longer exists, remove from archive
			del self.data[k]
			self._dirty = True
		
		# Title-based fallback search
		if title:
			clean = sanitize_filename(title, restricted=False).lower()
			keys_to_remove = []
			
			for kk, v in list(self.data.items()):
				if kk.endswith(f"_{container}"):
					p = Path(v["file_path"])
					if not p.exists():
						keys_to_remove.append(kk)
						continue
					
					if sanitize_filename(v.get("title", ""), restricted=False).lower() == clean:
						# Clean up missing files we found along the way
						for key_to_remove in keys_to_remove:
							del self.data[key_to_remove]
						if keys_to_remove:
							self._dirty = True
						return v
			
			# Clean up any missing files we found
			for key_to_remove in keys_to_remove:
				del self.data[key_to_remove]
			if keys_to_remove:
				self._dirty = True
		
		return None
	
	def add(self, vid: str, extractor: str, title: str, file_path: Path, container: str):
		"""Add a new entry to the archive."""
		k = self.key(vid, extractor, container)
		self.data[k] = {
			"id": vid,
			"extractor": extractor,
			"title": title,
			"format": container,
			"file_path": str(file_path),
			"download_date": file_path.stat().st_mtime if file_path.exists() else 0.0
		}
		self._dirty = True
	
	# Make ArchiveManager compatible with yt-dlp's archive expectations
	def __contains__(self, key):
		"""Support 'key in archive' checks from yt-dlp."""
		return key in self.data
	
	def __iter__(self):
		"""Support iteration over archive keys."""
		return iter(self.data)
	
	def keys(self):
		"""Return archive keys."""
		return self.data.keys()


def flat_entries(url: str, use_cookies: bool) -> list[dict]:
	"""Extract flat playlist entries (IDs + titles only) without heavy extractor work."""
	opts = {
		"extract_flat": True,         # <- no per-item player probing
		"dump_single_json": True,
		"quiet": True,
		"logger": _YDLLogger(),
		"socket_timeout": 15,
		"extractor_retries": 3,
	}
	if use_cookies:
		opts["cookiesfrombrowser"] = ("firefox", None, None, None)
	
	try:
		with YoutubeDL(opts) as ydl:
			info = ydl.extract_info(url, download=False)
		return (info.get("entries") if info else []) or []
	except Exception as e:
		print(f"    {C_WARN}Warning: Could not extract flat entries: {e}{C_RESET}")
		return []


def fast_copy_from_archive(url: str, base_dir: Path, container: str, archive_mgr: ArchiveManager) -> list[str]:
	"""Fast prepass: copy everything from archive, return missing IDs for download."""
	entries = flat_entries(url, use_cookies=is_youtube_music_liked(url))
	if not entries:
		return []
	
	# Create playlist folder
	if is_youtube_music_liked(url):
		playlist_dir = base_dir / "Liked Music"
	else:
		# Try to get playlist title from flat extraction
		playlist_title = "Playlist"  # fallback
		try:
			# Extract basic info to get playlist title
			temp_opts = {"quiet": True, "logger": _YDLLogger()}
			if is_youtube_music_liked(url):
				temp_opts["cookiesfrombrowser"] = ("firefox", None, None, None)
			
			with YoutubeDL(temp_opts) as ydl:
				info = ydl.extract_info(url, download=False)
				if info:
					playlist_title = info.get("playlist_title") or info.get("playlist") or playlist_title
		except Exception:
			pass
		
		playlist_dir = base_dir / sanitize_filename(playlist_title, restricted=False)
	
	playlist_dir.mkdir(parents=True, exist_ok=True)
	
	missing_ids = []
	copied_count = 0
	
	for e in entries:
		vid = e.get("id")
		title = e.get("title") or "unknown"
		if not vid:
			continue
		
		entry = archive_mgr.find(vid, e.get("extractor_key") or "YouTube", container, title)
		if entry:
			if optimized_copy_from_archive(entry, playlist_dir, container):
				copied_count += 1
		else:
			missing_ids.append(vid)
	
	if copied_count > 0:
		print(f"  📋 {C_OK}Copied {copied_count} files from archive{C_RESET}")
	
	if missing_ids:
		print(f"  📥 {C_DIM}Need to download {len(missing_ids)} new files{C_RESET}")
	
	return missing_ids


def optimized_copy_from_archive(archive_entry: dict, target_dir: Path, container: str) -> bool:
	"""Copy with hardlink optimization for same-volume files."""
	try:
		source_path = Path(archive_entry['file_path'])
		if not source_path.exists():
			return False
		
		# Determine target filename
		title = archive_entry['title']
		clean_title = sanitize_filename(title, restricted=False)
		
		# Determine extension based on format and source file
		if container in ("mp3", "native"):
			if container == "mp3":
				target_ext = ".mp3" if source_path.suffix.lower() == ".mp3" else source_path.suffix
			else:  # native
				target_ext = source_path.suffix
		else:
			target_ext = source_path.suffix or f".{container}"
		
		target_path = target_dir / f"{clean_title}{target_ext}"
		
		# Avoid copying to the same location
		if source_path.resolve() == target_path.resolve():
			return True
		
		# Try hardlink first (fast path on same volume)
		try:
			os.link(source_path, target_path)  # Windows supports this on NTFS
			print(f"    📎 {C_OK}Hardlinked from archive:{C_RESET} {target_path.name}")
		except Exception:
			# Fallback to copy if hardlink fails (different volumes, etc.)
			shutil.copy2(source_path, target_path)
			print(f"    📋 {C_OK}Copied from archive:{C_RESET} {target_path.name}")
		
		print(f"      {C_DIM}Source: {source_path}{C_RESET}")
		print(f"      {C_DIM}Target: {target_path}{C_RESET}")
		return True
		
	except Exception as e:
		print(f"    {C_WARN}Warning: Could not copy from archive: {e}{C_RESET}")
		return False


class _YDLLogger:
	def debug(self, msg): 
		# Filter super-chatty lines, but keep useful extractor messages
		low = msg.lower()
		if any(k in low for k in ("downloading", "extract", "playlist", "continuation", "api", "cookies")):
			print(f"    {C_DIM}{msg}{C_RESET}")
	def warning(self, msg): print(f"    {C_WARN}[warn] {msg}{C_RESET}")
	def error(self, msg):   print(f"    {C_ERR}[err ] {msg}{C_RESET}")


class Heartbeat:
	def __init__(self, label: str = "working…", interval: float = 2.0):
		self.label, self.interval, self._stop = label, interval, False
		
	def start(self):
		def run():
			import threading, time
			i = 0
			while not self._stop:
				i = (i + 1) % 4
				dots = "." * i + " " * (3 - i)
				print(f"\r  {self.label} {dots}", end="", flush=True)
				time.sleep(self.interval)
			print("\r" + " " * 40 + "\r", end="")
		import threading
		self._thr = threading.Thread(target=run, daemon=True)
		self._thr.start()
		
	def stop(self):
		self._stop = True
		if hasattr(self, "_thr"): 
			self._thr.join(timeout=0.2)

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
	return ("music.youtube.com" in u) and ("list=lm" in u or "liked" in u)


def outtmpl_for_unknown_playlist(base_dir: Path) -> str:
	"""Output template that works before we know playlist metadata."""
	# Let yt-dlp resolve folder name lazily; LM gets a fixed folder.
	return str(base_dir / "%(playlist_title|playlist|uploader|channel|id)s" / "%(title)s.%(ext)s")


def download_immediate(urls: list[str], base_dir: Path, container: str, fmt_type: str, fast_mode: bool = False) -> int:
	"""Download URLs immediately with fast copy prepass optimization."""
	print(f"  🚀 {C_OK}Starting optimized download mode (with fast copy prepass)...{C_RESET}")
	
	# Initialize archive manager once
	archive_mgr = ArchiveManager()
	
	# Common opts
	opts = ydl_opts_common(base_dir, container, fmt_type, False, fast_mode)
	opts.update({
		"lazy_playlist": True,         # fetch + download page-by-page
		"playlistreverse": False,
		"break_on_existing": True,     # Stop early when hitting existing files
		"break_per_url": True,         # Apply break_on_existing per URL
		"progress_with_newline": True,
		"logger": _YDLLogger(),
		"socket_timeout": 15,
		"extractor_retries": 3,
		"noprogress": False,
	})

	# Output template that works before we know playlist title
	opts["outtmpl"] = {"default": outtmpl_for_unknown_playlist(base_dir)}

	# If any URL is LM, force Firefox cookies for the real run
	if any(is_youtube_music_liked(u) for u in urls):
		print(f"  🍪 {C_OK}Auto-enabling Firefox cookies for Liked Music...{C_RESET}")
		opts["cookiesfrombrowser"] = ("firefox", None, None, None)

	total_ok = 0
	
	# Build archive from existing files in the download directory
	try:
		build_archive_from_existing_files_optimized(base_dir, container, archive_mgr)
	except Exception as e:
		print(f"    {C_WARN}Warning: Could not build archive from existing files: {e}{C_RESET}")

	for url in urls:
		print(f"\n{C_HEAD}➡ Processing: {url}{C_RESET}")
		
		# Fast copy prepass for playlists
		if "playlist" in url.lower() or "list=" in url.lower():
			print(f"  🔍 {C_DIM}Fast copy prepass: checking archive for existing files...{C_RESET}")
			missing_ids = fast_copy_from_archive(url, base_dir, container, archive_mgr)
			
			if not missing_ids:
				print(f"  ✅ {C_OK}All items satisfied from archive - no downloads needed!{C_RESET}")
				total_ok += 1
				continue
			
			# Only download the missing items
			if len(missing_ids) < 50:  # Don't spam for large playlists
				print(f"  📥 {C_DIM}Downloading {len(missing_ids)} missing items: {', '.join(missing_ids[:10])}{('...' if len(missing_ids) > 10 else '')}{C_RESET}")
			else:
				print(f"  📥 {C_DIM}Downloading {len(missing_ids)} missing items{C_RESET}")
			
			# Convert missing IDs to full URLs for download
			real_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in missing_ids]
		else:
			# Single video - process normally
			real_urls = [url]
		
		with SmartYoutubeDL(opts, base_dir, container, url, archive_mgr=archive_mgr) as ydl:
			# Use heartbeat around download to show continuous progress
			hb = Heartbeat("Processing")
			try:
				hb.start()
				print(f"  📥 {C_OK}Starting download...{C_RESET}")
				
				# For playlists with missing items, download only those
				res = ydl.download(real_urls)
				
				if res == 0:
					total_ok += 1
					print(f"  ✅ {C_OK}Download completed successfully{C_RESET}")
				else:
					print(f"    ⚠ {C_WARN}Download completed with warnings for: {url}{C_RESET}")
					
			except KeyboardInterrupt:
				print(f"\n{C_WARN}Download interrupted by user{C_RESET}")
				raise
			except Exception as e:
				print(f"    ✗ {C_ERR}Error downloading {url}: {e}{C_RESET}")
				continue
			finally:
				hb.stop()

	# Save archive once at the end
	archive_mgr.save()
	return total_ok


def should_retry_with_cookies(error_message: str, url: str) -> bool:
	"""Determine if we should retry a failed playlist download with cookies."""
	# Check if it's a playlist URL and the error suggests authentication issues
	is_playlist_url = ("playlist" in url.lower() or "list=" in url.lower())
	if not is_playlist_url:
		return False
	
	# Common error patterns that suggest private/restricted content
	error_lower = error_message.lower()
	auth_error_patterns = [
		"private",
		"unavailable", 
		"not available",
		"requires authentication",
		"sign in",
		"403",
		"forbidden",
		"restricted",
		"members-only",
		"this playlist is private"
	]
	
	return any(pattern in error_lower for pattern in auth_error_patterns)


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
	print(f"  {C_HEAD}[4]{C_RESET} Native (audio, fastest - no conversion)")
	while True:
		choice = prompt("Enter 1, 2, 3, or 4", default="1")
		if choice == "1":
			return ("mp3", "audio")
		elif choice == "2":
			return ("mkv", "video")
		elif choice == "3":
			return ("mp4", "video")
		elif choice == "4":
			return ("native", "audio")
		print(C_WARN + "Please enter 1, 2, 3, or 4." + C_RESET)


def split_urls(s: str) -> list[str]:
	# Allow space or newline separated multiple URLs
	parts = re.split(r"\s+", s.strip())
	return [p for p in parts if p]


def build_outtmpl(base_dir: Path, is_audio: bool, url: str = "", info: dict | None = None) -> str:
	if is_youtube_music_liked(url):
		liked_dir = base_dir / "Liked Music"
		liked_dir.mkdir(parents=True, exist_ok=True)
		return str(liked_dir / "%(title)s.%(ext)s")
		
	# If we already have playlist metadata, pick an explicit folder name now
	if info and (info.get("_type") == "playlist" or info.get("entries")):
		playlist_dir = base_dir / get_playlist_folder_name(url, info)
		playlist_dir.mkdir(parents=True, exist_ok=True)
		return str(playlist_dir / "%(title)s.%(ext)s")

	# If we *suspect* a playlist but don't have info yet, let yt-dlp resolve it
	if ("playlist" in url.lower() or "list=" in url.lower()) and not info:
		base_dir.mkdir(parents=True, exist_ok=True)
		# Use a robust fallthrough so yt-dlp fills whichever it knows
		return str(base_dir / "%(playlist_title|playlist|uploader|channel|id)s" / "%(title)s.%(ext)s")

	# Single item
	base_dir.mkdir(parents=True, exist_ok=True)
	return str(base_dir / "%(title)s.%(ext)s")


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


def find_in_archive(video_id: str, extractor: str, container: str, title: str | None = None) -> dict | None:
	"""Find a video in the archive for the specific format and return its info if the file still exists."""
	archive = load_archive()
	key = f"{extractor.lower()}_{video_id}_{container}"
	
	# First try exact key match
	if key in archive:
		entry = archive[key]
		file_path = Path(entry['file_path'])
		if file_path.exists():
			return entry
		else:
			# File no longer exists, remove from archive
			del archive[key]
			save_archive(archive)
	
	# If no exact match and we have a title, try title-based matching
	if title:
		# Clean the title for comparison (same as sanitize_filename does)
		clean_title = sanitize_filename(title, restricted=False).lower()
		
		# Look through all archive entries for this container
		keys_to_remove = []
		for arch_key, entry in archive.items():
			if arch_key.endswith(f"_{container}"):
				# Check if file still exists
				file_path = Path(entry['file_path'])
				if not file_path.exists():
					keys_to_remove.append(arch_key)
					continue
				
				# Compare titles
				archived_title = sanitize_filename(entry.get('title', ''), restricted=False).lower()
				if clean_title == archived_title:
					# Found a title match!
					return entry
		
		# Clean up any missing files we found
		if keys_to_remove:
			for key_to_remove in keys_to_remove:
				del archive[key_to_remove]
			save_archive(archive)
	
	return None


def copy_from_archive(archive_entry: dict, target_dir: Path, container: str) -> bool:
	"""Copy a file from archive location to target directory (calls optimized version)."""
	return optimized_copy_from_archive(archive_entry, target_dir, container)


def folder_name_from_info(info: dict) -> str:
	name = info.get("playlist_title") or info.get("uploader") or info.get("channel") or "Unknown"
	# Use yt-dlp's sanitizer to match file naming rules
	return sanitize_filename(str(name), restricted=False)


def get_playlist_folder_name(url: str, info: dict | None = None) -> str:
	"""Get the appropriate folder name for a playlist."""
	if is_youtube_music_liked(url):
		return "Liked Music"
	if info:
		name = info.get("playlist_title") or info.get("playlist") \
		       or info.get("uploader") or info.get("channel") or "Playlist"
		return sanitize_filename(str(name), restricted=False)
	return "Playlist"


def create_playlist_folder(base_dir: Path, url: str, info: dict | None = None) -> Path:
	"""Create and return the appropriate folder for a playlist download."""
	folder_name = get_playlist_folder_name(url, info)
	playlist_dir = base_dir / folder_name
	
	try:
		playlist_dir.mkdir(parents=True, exist_ok=True)
		print(f"  📁 Using playlist folder: {C_DIM}{folder_name}{C_RESET}")
		return playlist_dir
	except Exception as e:
		print(C_WARN + f"Warning: Could not create playlist folder '{folder_name}', using base directory: {e}" + C_RESET)
		return base_dir


def check_existing_file(base_dir: Path, info: dict, container: str) -> bool:
	"""Check if a file already exists based on the video info and format."""
	try:
		title = info.get("title", "unknown")
		# Use yt-dlp's sanitizer to match the actual filename that would be created
		clean_title = sanitize_filename(title, restricted=False)
		
		# Determine the expected extension
		if container == "mp3":
			extensions = [".mp3"]
		elif container == "native":
			extensions = [".m4a", ".opus", ".webm", ".mp3", ".aac"]  # Common audio formats
		else:
			extensions = [".mp4", ".m4v", ".mkv", ".webm", ".avi"]  # Common video formats
		
		# Check for existing files with any of the possible extensions
		for ext in extensions:
			potential_file = base_dir / f"{clean_title}{ext}"
			if potential_file.exists():
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
			print(f"\r    📥 {percent:.1f}% downloaded{speed_str}", end='', flush=True)
		else:
			# For streams without known total size
			downloaded = d.get('downloaded_bytes', 0)
			speed = d.get('speed', 0)
			if speed:
				speed_str = f" at {speed/1024/1024:.1f}MB/s"
			else:
				speed_str = ""
			print(f"\r    📥 {downloaded/1024/1024:.1f}MB downloaded{speed_str}", end='', flush=True)
	elif d['status'] == 'finished':
		filename = Path(d['filename']).name
		print(f"\r    ✅ {C_OK}Downloaded:{C_RESET} {filename}")
	elif d['status'] == 'error':
		filename = d.get('filename', 'unknown')
		print(f"\r    ❌ {C_ERR}Error downloading:{C_RESET} {Path(filename).name if filename != 'unknown' else filename}")
	elif d['status'] == 'processing':
		filename = Path(d.get('filename', 'file')).name
		print(f"    🔄 {C_DIM}Processing:{C_RESET} {filename}")
	elif d['status'] == 'extracting':
		print(f"    🔍 {C_DIM}Extracting video information...{C_RESET}")
	elif d['status'] == 'preparing':
		print(f"    ⚙️  {C_DIM}Preparing download...{C_RESET}")


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


def build_archive_from_existing_files_optimized(download_dir: Path, container: str, archive_mgr: ArchiveManager) -> None:
	"""Build archive from existing files using the optimized ArchiveManager."""
	try:
		# Determine extensions based on format
		if container == "mp3":
			extensions = ['.mp3']
		elif container == "native":
			extensions = ['.m4a', '.opus', '.webm', '.mp3', '.aac']
		else:
			extensions = ['.mp4', '.mkv', '.webm', '.avi']
		
		added_count = 0
		for file_path in download_dir.glob("*"):
			if file_path.is_file() and file_path.suffix.lower() in extensions:
				# Generate a stable key for existing files
				key = _stable_key_for_path(str(file_path.absolute()), container)
				
				# Check if already in archive
				if key not in archive_mgr.data:
					archive_mgr.data[key] = {
						'id': file_path.stem,
						'extractor': 'local',
						'title': file_path.stem,
						'format': container,
						'file_path': str(file_path.absolute()),
						'download_date': file_path.stat().st_mtime
					}
					archive_mgr._dirty = True
					added_count += 1
		
		if added_count > 0:
			print(f"    📁 {C_DIM}Added {added_count} existing files to archive{C_RESET}")
	except Exception as e:
		print(f"    {C_WARN}Warning: Could not build archive from existing files: {e}{C_RESET}")


def build_archive_from_existing_files(download_dir: Path, container: str) -> None:
	"""Build archive from existing files in the download directory."""
	try:
		archive = load_archive()
		# Determine extensions based on format
		if container == "mp3":
			extensions = ['.mp3']
		elif container == "native":
			extensions = ['.m4a', '.opus', '.webm', '.mp3', '.aac']
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
				f.write(line + "\n")
	except Exception:
		pass


class SmartYoutubeDL(YoutubeDL):
	"""Custom YoutubeDL class that uses JSON archive and copies existing files."""
	
	def __init__(self, params=None, base_dir=None, container=None, url=None, archive_mgr=None):
		super().__init__(params)
		self.base_dir = base_dir
		self.container = container
		self.url = url or ""
		self.skipped_count = 0
		self.downloaded_count = 0
		self.copied_count = 0
		self._playlist_info: dict | None = None
		self.archive = archive_mgr or ArchiveManager()
	
	def __exit__(self, *args):
		"""Ensure archive is saved when context manager exits."""
		try:
			# Save the archive
			self.archive.save()
		except Exception as e:
			print(f"    {C_WARN}Warning: Could not save archive on exit: {e}{C_RESET}")
		
		# Call parent's exit
		return super().__exit__(*args)
	
	def process_info(self, info_dict):
		"""Override to add archive checking and copy logic."""
		# Check if this is a single video entry (not a playlist)
		if info_dict.get('_type') != 'playlist' and self.base_dir and self.container:
			video_id = info_dict.get('id')
			extractor = info_dict.get('extractor_key', info_dict.get('extractor', 'generic'))
			title = info_dict.get('title', 'unknown')
			
			# Show which item we're processing
			print(f"  🎵 {C_DIM}Processing:{C_RESET} {title}")
			
			if video_id and extractor:
				# Check if we have this in our archive for the specific format
				archive_entry = self.archive.find(video_id, extractor, self.container, title)
				if archive_entry:
					print(f"    📋 {C_OK}Found in archive - skipping download{C_RESET}")
					print(f"    {C_DIM}Archive location: {archive_entry['file_path']}{C_RESET}")
					# Try to copy from archive
					# Determine target directory (playlist folder if applicable)
					target_dir = self.base_dir
					if hasattr(self, '_playlist_info') and self._playlist_info:
						target_dir = create_playlist_folder(self.base_dir, self.url, self._playlist_info)
					
					if copy_from_archive(archive_entry, target_dir, self.container):
						self.copied_count += 1
						return None  # Skip downloading
					else:
						print(f"    ⚠️  {C_WARN}Archive copy failed, will re-download{C_RESET}")
				
				# Check if file already exists in current directory
				target_dir = self.base_dir
				if hasattr(self, '_playlist_info') and self._playlist_info:
					target_dir = create_playlist_folder(self.base_dir, self.url, self._playlist_info)
				
				if check_existing_file(target_dir, info_dict, self.container):
					print(f"    ⏭️  {C_DIM}Skipping (file already exists locally){C_RESET}")
					self.skipped_count += 1
					return None  # Skip this video
			
			# If we get here, we need to download
			print(f"    📥 {C_DIM}Starting download...{C_RESET}")
		
		# Process normally (download)
		result = super().process_info(info_dict)
		
		# If download was successful, add to archive
		if result and info_dict.get('_type') != 'playlist':
			self.downloaded_count += 1
			title = info_dict.get('title', 'unknown')
			print(f"    ✅ {C_OK}Successfully downloaded{C_RESET}")
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
				file_path = None
				
				if self.container == "mp3":
					file_path = self.base_dir / f"{clean_title}.mp3"
				elif self.container == "native":
					# For native format, we need to check what file actually exists
					# Common audio extensions for native downloads
					possible_exts = [".m4a", ".opus", ".webm", ".mp3", ".aac"]
					for possible_ext in possible_exts:
						potential_path = self.base_dir / f"{clean_title}{possible_ext}"
						if potential_path.exists():
							file_path = potential_path
							break
				else:
					file_path = self.base_dir / f"{clean_title}.{self.container}"
				
				if file_path and file_path.exists():
					self.archive.add(video_id, extractor, title, file_path, self.container)
		except Exception as e:
			print(f"    {C_DIM}Note: Could not add to archive: {e}{C_RESET}")


def ydl_opts_common(base_dir: Path, container: str, fmt_type: str, use_firefox_cookies: bool, fast_mode: bool = False, url: str = "", info: dict | None = None) -> dict:
	is_audio = fmt_type == "audio"
	opts: dict = {
		"outtmpl": build_outtmpl(base_dir, is_audio, url, info),
		"restrictfilenames": False,
		"windowsfilenames": True,
		"noprogress": fast_mode,  # Reduce console writes in fast mode
		"ignoreerrors": True,
		"retries": 10,
		"fragment_retries": 10,
		"concurrent_fragment_downloads": 8,  # Bumped from 5 for better performance
		"continuedl": True,
		"writeinfojson": False,  # Disable individual JSON files
		"writethumbnail": not fast_mode,  # Skip thumbnails in fast mode
		"overwrites": False,
		"extract_flat": "in_playlist" if ("playlist" in url.lower() or "list=" in url.lower()) else False,  # Reduce per-item overhead for playlists
		"lazy_playlist": True,  # Enable lazy playlist processing for faster startup
		"playlistreverse": False,  # Ensure consistent playlist order
		"progress_hooks": [lambda d: download_progress_hook(d, base_dir, container)],
		"postprocessor_args": [
			"-metadata", "comment=Downloaded with yt-dlp wrapper",
			# VLC-friendly options to fix fast-forward issues
			"-avoid_negative_ts", "make_zero",
			"-fflags", "+discardcorrupt",
		],
		"logger": _YDLLogger(),
		"socket_timeout": 15,          # don't sit forever on a bad socket
		"extractor_retries": 3,        # retry different pathways
		"nocheckcertificate": False,   # leave True only if you *need* it
		"progress_with_newline": True, # prevents carriage-return lines from hiding output
	}

	if is_audio:
		if container == "native":
			# Native format: No conversion, fastest
			opts.update({
				"format": "bestaudio/best",
				"postprocessors": [],  # No post-processing at all
				"prefer_ffmpeg": True,
				"keepvideo": False,
			})
		else:
			# MP3 format
			postprocessors = [
				{
					"key": "FFmpegExtractAudio",
					"preferredcodec": "mp3",
					"preferredquality": "0",
				},
			]
			
			# Add metadata and thumbnail processing only if not in fast mode
			if not fast_mode:
				postprocessors.extend([
					{"key": "EmbedThumbnail"},
					{"key": "FFmpegMetadata"},
				])
			
			opts.update({
				"format": "bestaudio/best",
				"postprocessors": postprocessors,
				"prefer_ffmpeg": True,
				"keepvideo": False,
			})
	else:
		# Video settings optimized for container type
		video_postprocessors = []
		
		# Add metadata processing unless in fast mode
		if not fast_mode:
			video_postprocessors.append({"key": "FFmpegMetadata"})
		
		if container == "mkv":
			# MKV: Better seeking, can embed thumbnails reliably
			opts.update({
				"format": "bestvideo+bestaudio/best",
				"merge_output_format": "mkv",
				"remux_video": "mkv",  # Also remux single-stream downloads
			})
			if not fast_mode:
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


def download_urls(urls: list[str], base_dir: Path, container: str, fmt_type: str, force_firefox_cookies: bool, fast_mode: bool = False) -> int:
	# Check if any URLs are Liked Music - use immediate mode for better streaming
	liked_music_urls = [url for url in urls if is_youtube_music_liked(url)]
	regular_urls = [url for url in urls if not is_youtube_music_liked(url)]
	
	total_ok = 0
	
	# Process Liked Music URLs with immediate mode (no prepass)
	if liked_music_urls:
		print(f"\n🎵 {C_HEAD}Processing Liked Music URLs with streaming mode...{C_RESET}")
		total_ok += download_immediate(liked_music_urls, base_dir, container, fmt_type, fast_mode)
	
	# Process regular URLs with the existing logic (with prepass for better folder naming)
	if regular_urls:
		if liked_music_urls:
			print(f"\n📁 {C_HEAD}Processing other URLs with info prepass...{C_RESET}")
		total_ok += download_urls_with_prepass(regular_urls, base_dir, container, fmt_type, force_firefox_cookies, fast_mode)
	
	return total_ok


def download_urls_with_prepass(urls: list[str], base_dir: Path, container: str, fmt_type: str, force_firefox_cookies: bool, fast_mode: bool = False) -> int:
	total_ok = 0
	
	# Initialize archive manager once for all URLs
	archive_mgr = ArchiveManager()
	
	# Build archive from existing files in the download directory
	try:
		build_archive_from_existing_files_optimized(base_dir, container, archive_mgr)
	except Exception as e:
		print(f"    {C_WARN}Warning: Could not build archive from existing files: {e}{C_RESET}")

	for url in urls:
		print(f"\n{C_HEAD}➡ Processing: {url}{C_RESET}")
		print(f"  🔍 {C_DIM}Extracting playlist information...{C_RESET}")
		
		info = None
		is_playlist = False
		
		try:
			# Set up temporary extractor with cookies if needed
			temp_opts = {
				"quiet": False,               # <-- turn quiet OFF so we can see progress
				"no_warnings": False,
				"logger": _YDLLogger(),
				"socket_timeout": 15,
				"extractor_retries": 3,
			}
			
			# Check if we need Firefox cookies for this URL
			use_cookies_for_info = force_firefox_cookies or is_youtube_music_liked(url)
			if use_cookies_for_info:
				print(f"  🍪 {C_DIM}Loading Firefox cookies for authentication...{C_RESET}")
				temp_opts["cookiesfrombrowser"] = ("firefox", None, None, None)
			
			# First, extract info to determine if it's a playlist and get metadata
			print(f"  📊 {C_DIM}Connecting to YouTube Music...{C_RESET}")
			try:
				temp_ydl = YoutubeDL(temp_opts)
				
				# Add a timeout hint for user
				print(f"  ⏳ {C_DIM}This may take 10-30 seconds for large playlists...{C_RESET}")
				
				info = temp_ydl.extract_info(url, download=False)
				print(f"  ✅ {C_OK}Successfully extracted playlist information!{C_RESET}")
				
			except Exception as extract_error:
				print(f"  ❌ {C_WARN}Connection failed: {str(extract_error)[:100]}{'...' if len(str(extract_error)) > 100 else ''}{C_RESET}")
				raise extract_error
			
			# Determine if this is a playlist
			is_playlist = isinstance(info, dict) and (info.get("_type") == "playlist" or info.get("entries"))
			
			if is_playlist and info:
				print(f"  🎵 {C_HEAD}Playlist detected:{C_RESET} {info.get('playlist_title', 'Unknown Playlist')}")
				print(f"  📊 {C_DIM}Contains {len(info.get('entries', []))} items{C_RESET}")
				print(f"  📁 {C_DIM}Preparing download folder structure...{C_RESET}")
			else:
				print(f"  🎬 {C_HEAD}Single video detected{C_RESET}")
			
			# Build options with playlist info
			print(f"  ⚙️  {C_DIM}Configuring download options...{C_RESET}")
			opts = ydl_opts_common(base_dir, container, fmt_type, force_firefox_cookies, fast_mode, url, info if is_playlist else None)
			
		except Exception as e:
			print(f"  ⚠️  {C_WARN}Initial info extraction failed: {e}{C_RESET}")
			print(f"  🔄 {C_DIM}Will extract playlist info during download...{C_RESET}")
			# Fallback to basic options, let yt-dlp handle playlist detection during download
			try:
				# Make educated guess about playlist status from URL
				is_playlist = ("playlist" in url.lower() or "list=" in url)
				
				if is_playlist:
					print(f"  🎵 {C_HEAD}Playlist detected from URL - folder will be named from playlist title{C_RESET}")
					# Don't pass mock info - let yt-dlp's template system handle it
					opts = ydl_opts_common(base_dir, container, fmt_type, force_firefox_cookies, fast_mode, url, None)
				else:
					opts = ydl_opts_common(base_dir, container, fmt_type, force_firefox_cookies, fast_mode, url)
			except Exception as e2:
				print(f"    {C_ERR}Error setting up download options: {e2}{C_RESET}")
				continue
		
		print(f"  🚀 {C_OK}Starting download process...{C_RESET}")
		
		# Use our custom YoutubeDL class that uses JSON archive and copies files
		with SmartYoutubeDL(opts, base_dir, container, url, archive_mgr=archive_mgr) as ydl:
			# Set playlist info if available
			if info and is_playlist:
				ydl._playlist_info = info
			elif is_playlist and "list=LM" in url:
				# Set mock info for Liked Music
				ydl._playlist_info = {
					"_type": "playlist",
					"playlist_title": "Liked Music",
					"entries": []
				}
			
			try:
				# Auto-use cookies if it's a YT Music Liked URL
				if not force_firefox_cookies and is_youtube_music_liked(url):
					print(f"  🍪 {C_WARN}Auto-enabling Firefox cookies for Liked Music.{C_RESET}")
					ydl.params["cookiesfrombrowser"] = ("firefox", None, None, None)
				
				# Reset counters for this URL
				ydl.skipped_count = 0
				ydl.downloaded_count = 0
				ydl.copied_count = 0
				
				print(f"  🎯 {C_DIM}Checking archive for existing files...{C_RESET}")
				print(f"  📥 {C_OK}Beginning download/copy process...{C_RESET}")
				
				# Download with smart archive checking and copying
				res = ydl.download([url])
				
				# Report results with better feedback
				total_actions = ydl.downloaded_count + ydl.copied_count + ydl.skipped_count
				
				print(f"\n  📈 {C_HEAD}Summary for this URL:{C_RESET}")
				if ydl.downloaded_count > 0:
					print(f"    ✅ {C_OK}Downloaded (new files): {ydl.downloaded_count} file(s){C_RESET}")
				if ydl.copied_count > 0:
					print(f"    📋 {C_OK}Copied from archive (not downloaded): {ydl.copied_count} file(s){C_RESET}")
				if ydl.skipped_count > 0:
					print(f"    ⏭️  {C_DIM}Skipped (already exists locally): {ydl.skipped_count} file(s){C_RESET}")
				
				if total_actions > 0:
					archive_efficiency = (ydl.copied_count / total_actions) * 100
					if archive_efficiency > 0:
						print(f"    🎯 {C_DIM}Archive efficiency: {archive_efficiency:.1f}% (avoided {ydl.copied_count} downloads){C_RESET}")
					download_efficiency = (ydl.skipped_count / total_actions) * 100
					if download_efficiency > 0:
						print(f"    💾 {C_DIM}Already had locally: {download_efficiency:.1f}% ({ydl.skipped_count} files){C_RESET}")
				
				# Show total bandwidth/time saved
				total_saved = ydl.copied_count + ydl.skipped_count
				if total_saved > 0:
					print(f"    🚀 {C_OK}Total files not downloaded: {total_saved}/{total_actions} ({(total_saved/total_actions)*100:.1f}%){C_RESET}")
				
				# ydl.download returns 0 on success
				if res == 0:
					total_ok += 1
				else:
					print(f"    ⚠ {C_WARN}Download completed with warnings for: {url}{C_RESET}")
					
				# Generate M3U for playlists
				if is_playlist:
					try:
						playlist_dir = base_dir / get_playlist_folder_name(url, info) if info else base_dir
						if not playlist_dir.exists():
							playlist_dir = create_playlist_folder(base_dir, url, info)
						generate_m3u_for_playlist(info or {}, playlist_dir, container)
						print(f"    🎼 {C_DIM}Generated M3U playlist file in {playlist_dir.name}{C_RESET}")
					except Exception as e:
						print(f"    {C_DIM}Note: Could not generate M3U file: {e}{C_RESET}")
					
			except KeyboardInterrupt:
				print(f"\n{C_WARN}Download interrupted by user{C_RESET}")
				raise
			except Exception as e:
				# Check if we should retry with cookies for private playlists
				if (not force_firefox_cookies and 
				    not is_youtube_music_liked(url) and 
				    should_retry_with_cookies(str(e), url)):
					
					print(f"  🔒 {C_WARN}Download failed - playlist may be private/restricted{C_RESET}")
					print(f"  🔄 {C_DIM}Retrying with Firefox cookies for authentication...{C_RESET}")
					
					try:
						# Recreate YoutubeDL with cookies enabled
						opts["cookiesfrombrowser"] = ("firefox", None, None, None)
						with SmartYoutubeDL(opts, base_dir, container, url, archive_mgr=archive_mgr) as ydl_with_cookies:
							# Set playlist info if available
							if info and is_playlist:
								ydl_with_cookies._playlist_info = info
							elif is_playlist and "list=LM" in url:
								ydl_with_cookies._playlist_info = {
									"_type": "playlist",
									"playlist_title": "Liked Music",
									"entries": []
								}
							
							# Reset counters for retry
							ydl_with_cookies.skipped_count = 0
							ydl_with_cookies.downloaded_count = 0
							ydl_with_cookies.copied_count = 0
							
							print(f"  🍪 {C_OK}Authenticated successfully - resuming download...{C_RESET}")
							res = ydl_with_cookies.download([url])
							
							# Report results with better feedback
							total_actions = ydl_with_cookies.downloaded_count + ydl_with_cookies.copied_count + ydl_with_cookies.skipped_count
							
							print(f"\n  📈 {C_HEAD}Summary for this URL:{C_RESET}")
							if ydl_with_cookies.downloaded_count > 0:
								print(f"    ✅ {C_OK}Downloaded (new files): {ydl_with_cookies.downloaded_count} file(s){C_RESET}")
							if ydl_with_cookies.copied_count > 0:
								print(f"    📋 {C_OK}Copied from archive (not downloaded): {ydl_with_cookies.copied_count} file(s){C_RESET}")
							if ydl_with_cookies.skipped_count > 0:
								print(f"    ⏭️  {C_DIM}Skipped (already exists locally): {ydl_with_cookies.skipped_count} file(s){C_RESET}")
							
							if total_actions > 0:
								archive_efficiency = (ydl_with_cookies.copied_count / total_actions) * 100
								if archive_efficiency > 0:
									print(f"    🎯 {C_DIM}Archive efficiency: {archive_efficiency:.1f}% (avoided {ydl_with_cookies.copied_count} downloads){C_RESET}")
								download_efficiency = (ydl_with_cookies.skipped_count / total_actions) * 100
								if download_efficiency > 0:
									print(f"    💾 {C_DIM}Already had locally: {download_efficiency:.1f}% ({ydl_with_cookies.skipped_count} files){C_RESET}")
							
							# Show total bandwidth/time saved
							total_saved = ydl_with_cookies.copied_count + ydl_with_cookies.skipped_count
							if total_saved > 0:
								print(f"    🚀 {C_OK}Total files not downloaded: {total_saved}/{total_actions} ({(total_saved/total_actions)*100:.1f}%){C_RESET}")
							
							# Download successful
							if res == 0:
								total_ok += 1
								print(f"  ✅ {C_OK}Authentication retry successful!{C_RESET}")
							else:
								print(f"    ⚠ {C_WARN}Download completed with warnings for: {url}{C_RESET}")
								
							# Generate M3U for playlists (retry version)
							if is_playlist:
								try:
									playlist_dir = base_dir / get_playlist_folder_name(url, info) if info else base_dir
									if not playlist_dir.exists():
										playlist_dir = create_playlist_folder(base_dir, url, info)
									generate_m3u_for_playlist(info or {}, playlist_dir, container)
									print(f"    🎼 {C_DIM}Generated M3U playlist file in {playlist_dir.name}{C_RESET}")
								except Exception as m3u_error:
									print(f"    {C_DIM}Note: Could not generate M3U file: {m3u_error}{C_RESET}")
							
							# Continue to next URL after successful retry
							continue
							
					except Exception as retry_error:
						print(f"  ❌ {C_ERR}Retry with cookies also failed: {retry_error}{C_RESET}")
						print(f"    ✗ {C_ERR}Error downloading {url}: {e}{C_RESET}")
						# Continue with other URLs even if retry fails
						continue
				else:
					# Original error, no retry needed
					print(f"    ✗ {C_ERR}Error downloading {url}: {e}{C_RESET}")
					# Continue with other URLs even if one fails
					continue
	
	# Save archive once at the end
	archive_mgr.save()
	return total_ok


def show_help() -> None:
	"""Display help information and exit."""
	help_text = f"""
{C_HEAD}Interactive yt-dlp wrapper — MP3/MKV/MP4, playlists, cookies, and more{C_RESET}

{C_HEAD}USAGE:{C_RESET}
  python download.py [OPTIONS] [URLs...]

{C_HEAD}OPTIONS:{C_RESET}
  {C_ASK}--help{C_RESET}                    Show this help message and exit
  {C_ASK}--format{C_RESET} FORMAT           Download format: mp3, mkv, mp4, native (default: interactive)
  {C_ASK}--fast{C_RESET}                    Fast mode - skip thumbnails and metadata for speed
  {C_ASK}--non-interactive{C_RESET}         Auto-confirm prompts (for scripts/scheduled tasks)
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
  {C_ASK}native{C_RESET}  Audio in original format (fastest - no conversion)

{C_HEAD}EXAMPLES:{C_RESET}
  {C_DIM}# Interactive mode{C_RESET}
  python download.py

  {C_DIM}# Download audio only{C_RESET}
  python download.py --format mp3 "https://youtube.com/watch?v=..."

  {C_DIM}# Fast audio download (no thumbnails/metadata){C_RESET}
  python download.py --format native --fast "https://youtube.com/playlist?list=..."

  {C_DIM}# Download video with best seeking (MKV){C_RESET}
  python download.py --format mkv --outdir ./music "https://youtube.com/playlist?list=..."

  {C_DIM}# Use Firefox cookies for private playlists{C_RESET}
  python download.py --firefox-cookies --format mp3 "https://music.youtube.com/playlist?list=LM"

  {C_DIM}# Non-interactive mode for scripts{C_RESET}
  python download.py --non-interactive --format native --fast --file urls.txt

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
	#   --format mp3|mkv|mp4|native
	#   --fast                    (fast mode - skip thumbnails/metadata)
	#   --non-interactive         (auto-confirm prompts)
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
		"fast": False,
		"non_interactive": False,
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
		elif tok == "--fast":
			args["fast"] = True
			i += 1
		elif tok == "--non-interactive":
			args["non_interactive"] = True
			i += 1
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
	"""Display information about the archive using optimized ArchiveManager."""
	archive_mgr = ArchiveManager()
	archive_path = get_appdata_archive_path()
	
	print(f"{C_HEAD}Archive Information:{C_RESET}")
	print(f"  Location: {C_DIM}{archive_path}{C_RESET}")
	print(f"  Total entries: {C_DIM}{len(archive_mgr.data)}{C_RESET}")
	
	if archive_mgr.data:
		mp3_count = sum(1 for entry in archive_mgr.data.values() if entry.get('format') == 'mp3')
		mp4_count = sum(1 for entry in archive_mgr.data.values() if entry.get('format') == 'mp4')
		mkv_count = sum(1 for entry in archive_mgr.data.values() if entry.get('format') == 'mkv')
		native_count = sum(1 for entry in archive_mgr.data.values() if entry.get('format') == 'native')
		local_count = sum(1 for entry in archive_mgr.data.values() if entry.get('extractor') == 'local')
		
		print(f"  MP3 files: {C_DIM}{mp3_count}{C_RESET}")
		print(f"  MP4 files: {C_DIM}{mp4_count}{C_RESET}")
		print(f"  MKV files: {C_DIM}{mkv_count}{C_RESET}")
		print(f"  Native files: {C_DIM}{native_count}{C_RESET}")
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
	"""Scan a directory and add all MP3/MP4 files to the archive using optimized ArchiveManager."""
	try:
		dir_path = Path(directory_path)
		if not dir_path.exists():
			print(f"    {C_ERR}Directory not found: {directory_path}{C_RESET}")
			return False
		
		if not dir_path.is_dir():
			print(f"    {C_ERR}Path is not a directory: {directory_path}{C_RESET}")
			return False
		
		print(f"{C_HEAD}Scanning directory: {dir_path}{C_RESET}")
		
		# Supported file extensions
		audio_extensions = ['.mp3', '.m4a', '.aac', '.flac', '.wav']
		video_extensions = ['.mp4', '.mkv', '.webm', '.avi', '.mov']
		all_extensions = audio_extensions + video_extensions
		
		archive_mgr = ArchiveManager()
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
					for entry in archive_mgr.data.values()
				)
				
				if not already_exists:
					archive_mgr.data[key] = {
						'id': file_path.stem,
						'extractor': 'local',
						'title': file_path.stem,
						'format': container,
						'file_path': abs_path,
						'download_date': file_path.stat().st_mtime
					}
					archive_mgr._dirty = True
					added_count += 1
					print(f"  📁 Added: {file_path.name}")
				else:
					print(f"  ⏭️  Already in archive: {file_path.name}")
		
		# Save the updated archive
		archive_mgr.save()
		
		print(f"{C_OK}✓ Added {added_count} new files to archive{C_RESET}")
		if added_count == 0:
			print(f"    {C_DIM}(All files were already in archive){C_RESET}")
		
		return True
		
	except Exception as e:
		print(f"    {C_ERR}Error scanning directory: {e}{C_RESET}")
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
			elif args["format"] == "native":
				container, fmt_type = ("native", "audio")
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
	if args["fast"]:
		print("  Mode:      " + C_DIM + "Fast (no thumbnails/metadata)" + C_RESET)
	print()

	# Confirm
	try:
		if args["non_interactive"]:
			print(C_DIM + "Non-interactive mode: proceeding automatically" + C_RESET)
		else:
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
		ok = download_urls(urls, base_dir, container, fmt_type, use_firefox_cookies, args["fast"])
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
