;-------------------------------------------------------------------------------
; Isam AULauncher - UNIVERSAL ONLINE NSIS installer
; Compile with: makensis.exe installer\IsamAU-Universal.nsi
;
; Always installs the latest version by reading LAUNCHER_VERSION from GitHub.
; Never needs recompiling - one installer works for all releases.
;-------------------------------------------------------------------------------

!include "MUI2.nsh"
!include "LogicLib.nsh"

!define APP_NAME      "Isam AULauncher"
!define APP_SHORT     "Isam AULauncher"
!define COMPANY       "Isam"
!define VERSION_URL   "https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/refs/heads/main/LAUNCHER_VERSION"
!define GITHUB_BASE   "https://github.com/isam-ahmed0/Isam-AULauncher/releases/download"

!ifndef ROOT
  !define ROOT "${__FILEDIR__}\.."
!endif
!define SRC_ICON      "${ROOT}\src\launcher\resources\icon.ico"
!define SIDEBAR_BMP   "${ROOT}\installer\sidebar.bmp"

Name    "${APP_NAME}"
OutFile "${ROOT}\dist\IsamAU-Setup.exe"

InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "Install_Location"

RequestExecutionLevel user
Unicode True
SetCompressor /SOLID lzma

Icon    "${SRC_ICON}"
UninstallIcon "${SRC_ICON}"

BrandingText "Isam Installer"

; Placeholder version - overwritten at runtime
VIProductVersion "0.0.0.0"
VIAddVersionKey "ProductName"    "${APP_NAME}"
VIAddVersionKey "CompanyName"     "${COMPANY}"
VIAddVersionKey "LegalCopyright"  "Copyright (c) 2026 ${COMPANY}"

;------------------------------- Modern UI 2 -------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON   "${SRC_ICON}"
!define MUI_UNICON "${SRC_ICON}"

!define MUI_WELCOMEFINISHPAGE_BITMAP "${SIDEBAR_BMP}"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${SIDEBAR_BMP}"

!define MUI_WELCOMEPAGE_TITLE "Welcome"
!define MUI_WELCOMEPAGE_TEXT "A clean, modern launcher for Among Us.$\r$\n$\r$\nThis installer will download the latest version from the internet."

!define MUI_FINISHPAGE_TITLE "Done"
!define MUI_FINISHPAGE_TEXT "Setup is complete."
!define MUI_FINISHPAGE_RUN "$INSTDIR\IsamAULauncher.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME} now"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

;------------------------------- Runtime variables --------------------------
Var INST_VERSION

Function .onInit
  InitPluginsDir
  CreateDirectory "$PLUGINSDIR"

  ; --- Resolve latest version from GitHub (plain text file, no API) ---
  DetailPrint "Checking for latest version..."

  ; Force TLS 1.2
  System::Call 'wininet::InternetSetOption(0, 11, 0, 0) i'

  ; Download version file (3 bytes, instant)
  System::Call 'urlmon::URLDownloadToFile(0, t"${VERSION_URL}", t"$PLUGINSDIR\_version.txt", i0, i0) i .r0'

  ${If} $0 != "0"
    MessageBox MB_ICONSTOP "Could not check for updates. Please check your internet connection and try again."
    Quit
  ${EndIf}

  ; Read version from file
  FileOpen $1 "$PLUGINSDIR\_version.txt" r
  ${If} $1 == ""
    MessageBox MB_ICONSTOP "Could not determine latest version."
    Quit
  ${EndIf}
  FileRead $1 $INST_VERSION
  FileClose $1

  ; Trim trailing \r\n
  StrCpy $INST_VERSION $INST_VERSION -2

  ${If} $INST_VERSION == ""
    MessageBox MB_ICONSTOP "Could not determine latest version."
    Quit
  ${EndIf}

  DetailPrint "Latest version: $INST_VERSION"
FunctionEnd

;------------------------------- Components --------------------------------
Section "Isam AULauncher (required)" SecMain
  SectionIn RO

  ; --- Download zip via PowerShell (URL baked in by NSIS FileWrite) ---
  DetailPrint "Downloading $INST_VERSION..."
  DetailPrint "This may take a few minutes..."

  FileOpen $0 "$PLUGINSDIR\_download.ps1" w
  FileWrite $0 '$ErrorActionPreference = "Stop"$\r$\n'
  FileWrite $0 '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12$\r$\n'
  FileWrite $0 'ProgressPreference = "SilentlyContinue"$\r$\n'
  FileWrite $0 'Invoke-WebRequest -Uri "${GITHUB_BASE}/$INST_VERSION/IsamAU-All.zip" -OutFile "$PLUGINSDIR\IsamAU-All.zip" -UseBasicParsing$\r$\n'
  FileClose $0

  ; Redirect all output to log file to prevent nsExec buffer overflow
  nsExec::ExecToStack 'cmd /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\_download.ps1" > "$PLUGINSDIR\_download.log" 2>&1'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_ICONSTOP "Download failed (error $0). Please check your internet connection and try again."
    Quit
  ${EndIf}

  ; Verify download
  IfFileExists "$PLUGINSDIR\IsamAU-All.zip" 0 download_failed
    Goto download_ok
  download_failed:
    MessageBox MB_ICONSTOP "Download failed. The file was not created."
    Quit
  download_ok:
  DetailPrint "Download complete."

  ; --- Extract via PowerShell (built-in, no .bat files) ---
  DetailPrint "Extracting files..."
  CreateDirectory "$PLUGINSDIR\extracted"

  FileOpen $0 "$PLUGINSDIR\_extract.ps1" w
  FileWrite $0 'Expand-Archive -Path "$PLUGINSDIR\IsamAU-All.zip" -DestinationPath "$PLUGINSDIR\extracted" -Force$\r$\n'
  FileClose $0

  nsExec::ExecToStack 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\_extract.ps1"'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_ICONSTOP "Extraction failed. Please try again."
    Quit
  ${EndIf}
  DetailPrint "Extraction complete."

  ; --- Copy launcher files ---
  DetailPrint "Installing launcher..."
  SetOutPath "$INSTDIR"
  nsExec::ExecToStack 'cmd /c xcopy /E /Y "$PLUGINSDIR\extracted\IsamAULauncher\*" "$INSTDIR\"'
  Pop $0

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APP_SHORT}"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\${APP_SHORT}.lnk" "$INSTDIR\IsamAULauncher.exe"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\Uninstall ${APP_SHORT}.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName"     "${APP_NAME} $INST_VERSION"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion"  "$INST_VERSION"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher"       "${COMPANY}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon"     "$INSTDIR\icon.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1

  WriteRegStr HKCU "Software\${APP_NAME}" "Install_Location" "$INSTDIR"
SectionEnd

Section "Itch Login Fixer" SecFixer
  SectionIn RO
  DetailPrint "Installing Itch Login Fixer..."
  SetOutPath "$INSTDIR\Fixer"
  nsExec::ExecToStack 'cmd /c xcopy /E /Y "$PLUGINSDIR\extracted\Itch_Login_Fixer\*" "$INSTDIR\Fixer\"'
  Pop $0
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\Itch Login Fixer.lnk" "$INSTDIR\Fixer\Itch_Login_Fixer.exe"
SectionEnd

Section "Support tools (7-zip + mods)" SecTools
  SectionIn RO
  DetailPrint "Installing support tools..."
  SetOutPath "$INSTDIR"
  nsExec::ExecToStack 'cmd /c copy /Y "$PLUGINSDIR\extracted\7z.exe" "$INSTDIR\7z.exe"'
  Pop $0
  nsExec::ExecToStack 'cmd /c copy /Y "$PLUGINSDIR\extracted\bepmods.zip" "$INSTDIR\bepmods.zip"'
  Pop $0
SectionEnd

Section /o "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${APP_SHORT}.lnk" "$INSTDIR\IsamAULauncher.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}    "Core launcher files (required). Downloaded from the internet."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecFixer}   "Itch.io login fix tool."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecTools}   "7-Zip and BepInEx mod files."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on your Desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  Delete "$SMPROGRAMS\${APP_SHORT}\${APP_SHORT}.lnk"
  Delete "$SMPROGRAMS\${APP_SHORT}\Uninstall ${APP_SHORT}.lnk"
  Delete "$SMPROGRAMS\${APP_SHORT}\Itch Login Fixer.lnk"
  RMDir  "$SMPROGRAMS\${APP_SHORT}"

  Delete "$DESKTOP\${APP_SHORT}.lnk"

  RMDir  /r "$INSTDIR"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd
