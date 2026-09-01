@echo off
REM sign-installer.bat — Sign the NSIS installer with a self-signed certificate
REM Usage: sign-installer.bat [path-to-exe]
REM   Default: signs IsamAU-Setup.exe in the project root

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0.."
set "CERT_FILE=%PROJECT_DIR%\release\signing-cert.pfx"
set "TARGET=%~1"

if "%TARGET%"=="" set "TARGET=%PROJECT_DIR%\dist\IsamAU-Setup.exe"

REM Find signtool.exe
set "SIGNTOOL="
for /d %%V in ("C:\Program Files (x86)\Windows Kits\10\bin\*") do (
    if exist "%%V\x64\signtool.exe" set "SIGNTOOL=%%V\x64\signtool.exe"
)
if "%SIGNTOOL%"=="" (
    echo ERROR: signtool.exe not found. Install Windows SDK.
    exit /b 1
)

if not exist "%CERT_FILE%" (
    echo ERROR: Certificate not found at %CERT_FILE%
    echo Run build\create-cert.ps1 first to generate the certificate.
    exit /b 1
)

if not exist "%TARGET%" (
    echo ERROR: Target file not found: %TARGET%
    exit /b 1
)

echo.
echo === Isam AULauncher — Sign Installer ===
echo.
echo   Signtool: %SIGNTOOL%
echo   Cert:     %CERT_FILE%
echo   Target:   %TARGET%
echo.

set /p "SIGN_PASS=Enter certificate password: "

echo.
echo Signing...
"%SIGNTOOL%" sign /f "%CERT_FILE%" /p "%SIGN_PASS%" /fd SHA256 /d "Isam AULauncher" "%TARGET%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo SIGNING FAILED
    exit /b 1
)

echo.
echo Signed successfully!
echo.

REM Verify signature
"%SIGNTOOL%" verify /pa "%TARGET%"

echo.
