@echo off
REM One-click launcher for the Infrastructure Reliability Lab console.
cd /d "%~dp0"
where python >nul 2>nul || (echo Python not found on PATH. Install Python 3.12+ and retry. & pause & exit /b 1)
python -m pip install -q -r requirements.txt
python lab_gui.py
pause
