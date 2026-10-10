@echo off
REM Shared version reader. Call from a build script that has already cd'd to the
REM repo root:   call "%~dp0_version.bat"
REM
REM Exports two variables to the caller:
REM   VERSION       exact LAUNCHER_VERSION from src\launcher\config.py (the tag /
REM                 display string, e.g. 1.0-beta.1)
REM   FILE_VERSION  numeric X.X.X.X for NSIS VIProductVersion / FileVersion
setlocal

set "VERSION="
for /f "tokens=2 delims== " %%v in ('findstr /B "LAUNCHER_VERSION =" src\launcher\config.py') do set "VERSION=%%~v"
set "VERSION=%VERSION:"=%"
if not defined VERSION set "VERSION=0.1"

REM Derive a numeric file version: drop a prerelease suffix (-... or +...),
REM keep up to four dot-separated fields, pad the rest with 0.
REM "1.0-beta.1" -> "1.0.0.0";  "0.7-1" -> "0.7.0.0";  "2.1.3" -> "2.1.3.0"
set "VERBASE=%VERSION%"
for /f "tokens=1 delims=-+" %%a in ("%VERSION%") do set "VERBASE=%%a"
set "V1=0" & set "V2=0" & set "V3=0" & set "V4=0"
for /f "tokens=1,2,3,4 delims=." %%a in ("%VERBASE%") do (
  if not "%%a"=="" set "V1=%%a"
  if not "%%b"=="" set "V2=%%b"
  if not "%%c"=="" set "V3=%%c"
  if not "%%d"=="" set "V4=%%d"
)
set "FILE_VERSION=%V1%.%V2%.%V3%.%V4%"

endlocal & set "VERSION=%VERSION%" & set "FILE_VERSION=%FILE_VERSION%"
