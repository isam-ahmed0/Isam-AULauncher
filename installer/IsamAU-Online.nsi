;-------------------------------------------------------------------------------
; Isam AULauncher - ONLINE NSIS installer
; Compile with: makensis.exe installer\IsamAU-Online.nsi
;
; Downloads all files from GitHub Releases during install.
; Uses nsExec for direct command execution (no .bat file intermediaries).
;-------------------------------------------------------------------------------

!include "MUI2.nsh"
!include "LogicLib.nsh"

!define APP_NAME      "Isam AULauncher"
!define APP_SHORT     "Isam AULauncher"
!define COMPANY       "Isam"
!ifndef VERSION
  !define VERSION     "0.6"
!endif
!define VERSION_DOT   "${VERSION}.0.0"

; Repo root = folder above this script (overridden by /DROOT= in build scripts)
!ifndef ROOT
  !define ROOT "${__FILEDIR__}\.."
!endif
!define SRC_ICON      "${ROOT}\src\launcher\resources\icon.ico"
!define SIDEBAR_BMP   "${ROOT}\installer\sidebar.bmp"

; Download URL - GitHub Releases
!define DOWNLOAD_URL  "https://github.com/isam-ahmed0/Isam-AULauncher/releases/download/${VERSION}/IsamAU-All.zip"

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

VIProductVersion "${VERSION_DOT}"
VIAddVersionKey "ProductName"    "${APP_NAME}"
VIAddVersionKey "FileDescription" "${APP_NAME} ${VERSION} (Online)"
VIAddVersionKey "FileVersion"     "${VERSION_DOT}"
VIAddVersionKey "ProductVersion"  "${VERSION}"
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

Function .onInit
  InitPluginsDir
  CreateDirectory "$PLUGINSDIR"
FunctionEnd

;------------------------------- Components --------------------------------
Section "Isam AULauncher (required)" SecMain
  SectionIn RO

  ; --- Download via PowerShell (handles GitHub redirects natively) ---
  DetailPrint "Downloading files from GitHub..."
  DetailPrint "URL: ${DOWNLOAD_URL}"
  nsExec::ExecToStack 'powershell -NoProfile -Command "ProgressPreference = SilentlyContinue; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri &quot;${DOWNLOAD_URL}&quot; -OutFile &quot;$PLUGINSDIR\IsamAU-All.zip&quot; -UseBasicParsing"'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_ICONSTOP "Download failed. Please check your internet connection and try again."
    Quit
  ${EndIf}

  ; --- Extract ---
  DetailPrint "Extracting files..."
  CreateDirectory "$PLUGINSDIR\extracted"
  nsExec::ExecToStack 'cmd /c "$WINDIR\System32\tar.exe" xf "$PLUGINSDIR\IsamAU-All.zip" -C "$PLUGINSDIR\extracted"'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_ICONSTOP "Extraction failed. Please try again."
    Quit
  ${EndIf}

  ; --- Copy launcher files ---
  DetailPrint "Installing launcher..."
  SetOutPath "$INSTDIR"
  nsExec::ExecToStack 'cmd /c xcopy /E /Y "$PLUGINSDIR\extracted\IsamAULauncher\*" "$INSTDIR\"'
  Pop $0

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APP_SHORT}"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\${APP_SHORT}.lnk" "$INSTDIR\IsamAULauncher.exe"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\Uninstall ${APP_SHORT}.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName"     "${APP_NAME} ${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion"  "${VERSION}"
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

;------------------------------- Component descriptions --------------------
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}    "Core launcher files (required). Downloaded from the internet."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecFixer}   "Itch.io login fix tool."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecTools}   "7-Zip and BepInEx mod files."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on your Desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;------------------------------- Uninstall --------------------------------
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
