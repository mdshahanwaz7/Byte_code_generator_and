@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
start "" pythonw gui\app.py
