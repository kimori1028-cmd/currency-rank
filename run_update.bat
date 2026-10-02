@echo off
REM Daily update: tests -> fetch -> rebuild site data. ASCII+CRLF only.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python updater\test_quality.py >> update.log 2>&1
if errorlevel 1 (
  echo %date% %time% tests failed, update skipped >> update.log
  exit /b 1
)
python updater\update.py >> update.log 2>&1
