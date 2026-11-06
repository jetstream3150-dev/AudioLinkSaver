@echo off
cd /d "%~dp0"
py -3.12 -m pip install -r requirements-build.txt
if errorlevel 1 pause & exit /b 1
py -3.12 build_windows.py
pause
