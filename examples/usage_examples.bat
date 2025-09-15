@echo off
REM Advanced download script examples
REM This file demonstrates various ways to use the yt-dlp wrapper

echo yt-dlp Wrapper - Usage Examples
echo ================================
echo.

:menu
echo Select an example to run:
echo.
echo 1. Download single video as MP3
echo 2. Download playlist as MKV (best seeking)
echo 3. Download with Firefox cookies (private playlists)
echo 4. Batch download from URL file
echo 5. Add existing files to archive
echo 6. Show archive information
echo 7. Interactive mode (default)
echo 8. Exit
echo.

set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto single_mp3
if "%choice%"=="2" goto playlist_mkv
if "%choice%"=="3" goto with_cookies
if "%choice%"=="4" goto batch_download
if "%choice%"=="5" goto add_to_archive
if "%choice%"=="6" goto show_archive
if "%choice%"=="7" goto interactive
if "%choice%"=="8" goto exit
goto menu

:single_mp3
echo.
echo Example 1: Download single video as MP3
echo ========================================
set /p url="Enter YouTube URL: "
python download.py --format mp3 --outdir "music" "%url%"
echo.
pause
goto menu

:playlist_mkv
echo.
echo Example 2: Download playlist as MKV
echo ===================================
set /p url="Enter playlist URL: "
python download.py --format mkv --outdir "videos" "%url%"
echo.
pause
goto menu

:with_cookies
echo.
echo Example 3: Download with Firefox cookies
echo ========================================
echo This is useful for private playlists like YouTube Music Liked Songs
set /p url="Enter private playlist URL: "
python download.py --firefox-cookies --format mp3 --outdir "private_music" "%url%"
echo.
pause
goto menu

:batch_download
echo.
echo Example 4: Batch download from URL file
echo =======================================
echo Make sure you have a file with URLs (one per line)
set /p file="Enter URL file path (or press Enter for examples\urls.txt): "
if "%file%"=="" set file="examples\urls.txt"
set /p format="Enter format (mp3/mkv/mp4): "
if "%format%"=="" set format="mp3"
python download.py --file "%file%" --format "%format%" --outdir "batch_downloads"
echo.
pause
goto menu

:add_to_archive
echo.
echo Example 5: Add existing files to archive
echo ========================================
echo This prevents re-downloading files you already have
set /p dir="Enter directory path to scan: "
python download.py --load "%dir%"
echo.
pause
goto menu

:show_archive
echo.
echo Example 6: Show archive information
echo ===================================
python download.py --show-archive
echo.
pause
goto menu

:interactive
echo.
echo Example 7: Interactive mode
echo ===========================
echo Running interactive mode (default behavior)
python download.py
echo.
pause
goto menu

:exit
echo.
echo Additional examples:
echo.
echo # Clear archive by name
echo python download.py --clear "Artist Name"
echo.
echo # Clear archive by date range
echo python download.py --clear "2024-01-01" "2024-12-31"
echo.
echo # Backup archive
echo python download.py --backup
echo.
echo # Download to specific directory
echo python download.py --format mp4 --outdir "C:\Users\%USERNAME%\Videos" "URL_HERE"
echo.
echo Thanks for using yt-dlp wrapper!
pause
