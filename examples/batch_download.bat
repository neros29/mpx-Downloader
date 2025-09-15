@echo off
REM Batch file for downloading from a URL list
REM Usage: batch_download.bat [format] [output_directory]

set FORMAT=%1
set OUTDIR=%2

if "%FORMAT%"=="" set FORMAT=mp3
if "%OUTDIR%"=="" set OUTDIR=downloads

echo Starting batch download...
echo Format: %FORMAT%
echo Output Directory: %OUTDIR%

REM Create output directory if it doesn't exist
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

REM Run the download script
python download.py --file examples\urls.txt --format %FORMAT% --outdir "%OUTDIR%"

echo.
echo Batch download completed!
echo Files saved to: %OUTDIR%
pause
