@echo off
REM Build the Itch Login Fixer with Cx_Freeze.
REM
REM Note: Cx_Freeze builds both launcher + fixer together (shared lib/).
REM This script is a convenience alias — it builds everything.
REM
REM Requirements:
REM   1. Python on PATH (or activate your venv)
REM   2. pip install -r build\requirements.txt
REM
REM Produces: dist\IsamAULauncher_cx\Itch_Login_Fixer.exe
setlocal
cd /d "%~dp0.."

if not exist "dist" mkdir dist

echo ============================================================
echo  Building with Cx_Freeze...
echo ============================================================
python build\cx_setup.py build_exe --build-exe=dist\IsamAULauncher_cx
if errorlevel 1 (
  echo.
  echo Cx_Freeze build FAILED.
  exit /b 1
)

echo.
echo ============================================================
echo  Built: dist\IsamAULauncher_cx\Itch_Login_Fixer.exe
echo ============================================================
pause
