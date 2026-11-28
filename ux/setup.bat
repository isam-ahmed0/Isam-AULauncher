@echo off
REM Double-click wrapper for the CrewLauncher Windows installer/updater.
REM Usage: setup.bat [install|update|uninstall|is-installed] [-Silent] [-Online]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
exit /b %ERRORLEVEL%
