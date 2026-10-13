@echo off
cd /d "%~dp0"
if exist FH2-FPS-Unlocker.exe (
    start "" FH2-FPS-Unlocker.exe --compatibility-report
) else (
    py -3 unlock.py --compatibility-report
    pause
)
