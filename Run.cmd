@echo off
cd /d "%~dp0"
py -3 unlock.py %*
if errorlevel 1 pause
