;-------------------------------------------------------------------------------
; Isam AULauncher - ONLINE NSIS installer
; Compile with: makensis.exe installer\IsamAU-Online.nsi
;
; Downloads all files from GitHub Releases during install.
; Requires: 7z.exe bundled in installer for extraction.
;-------------------------------------------------------------------------------

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define APP_NAME      "Isam AULauncher"
!define APP_SHORT     "Isam AULauncher"
!define COMPANY       "Isam"
!ifndef VERSION
  !define VERSION     "0.1"
!endif
!define VERSION_DOT   "${VERSION}.0.0"

; Repo root = folder above this script (overridden by /DROOT= in build scripts)
!ifndef ROOT
  !define ROOT "${__FILEDIR__}\.."
!endif
!define SRC_ICON      "${ROOT}\src\launcher\resources\icon.ico"
!define SIDEBAR_BMP   "${ROOT}\installer\sidebar.bmp"
!define SEVENZ_EXE    "${ROOT}\release\7z.exe"

; Download URL — single zip with everything
!define DOWNLOAD_URL  "https://github.com/isam-ahmed0/Isam-AULauncher/releases/download/${VERSION}/IsamAU-All.zip"

Name    "${APP_NAME}"
OutFile "${ROOT}\dist\IsamAU-Online.exe"

InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "Install_Location"

RequestExecutionLevel user
Unicode True
SetCompressor /SOLID lzma

Icon    "${SRC_ICON}"
UninstallIcon "${SRC_ICON}"

; Replace "Nullsoft Install System" branding
BrandingText "Isam Installer"

; Installer / uninstaller metadata
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

; Custom sidebar image
!define MUI_WELCOMEFINISHPAGE_BITMAP "${SIDEBAR_BMP}"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${SIDEBAR_BMP}"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome"
!define MUI_WELCOMEPAGE_TEXT "A clean, modern launcher for Among Us.$\r$\n$\r$\nThis installer will download the latest version from the internet."

; Finish page
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

;------------------------------- Pre-install: kill running launcher --------
Function .onInit
  ; Kill any running launcher so files are not locked during update
  nsExec::ExecToStack 'taskkill /F /IM IsamAULauncher.exe'
  Pop $0
  Sleep 500
FunctionEnd

;------------------------------- Download & Extract -------------------------
Section "Isam AULauncher (required)" SecMain
  SectionIn RO

  ; Create temp directory for download
  InitPluginsDir
  DetailPrint "Preparing download..."
  CreateDirectory "$PLUGINSDIR"

  ; Bundle 7z.exe into plugins dir for extraction
  DetailPrint "Setting up extraction tool..."
  SetOutPath "$PLUGINSDIR"
  File "/oname=7z.exe" "${SEVENZ_EXE}"

  ; Download the combined zip
  DetailPrint "Downloading IsamAU-All.zip (this may take a while)..."
  nsis::Download /DETAILED "${DOWNLOAD_URL}" "$PLUGINSDIR\IsamAU-All.zip"
  Pop $0
  ${If} $0 != "success"
    MessageBox MB_ICONSTOP "Download failed. Please check your internet connection and try again.$\r$\n$\r$\nError: $0"
    Abort "Download failed"
  ${EndIf}

  ; Extract to install directory
  DetailPrint "Extracting files..."
  SetOutPath "$INSTDIR"
  nsExec::ExecToStack '"$PLUGINSDIR\7z.exe" x "$PLUGINSDIR\IsamAU-All.zip" -o"$INSTDIR" -y'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_ICONSTOP "Extraction failed. Please try again."
    Abort "Extraction failed"
  ${EndIf}

  ; The zip contains IsamAULauncher/, Itch_Login_Fixer/, 7z.exe, bepmods.zip
  ; Move files from subfolders to install root
  DetailPrint "Organizing files..."
  nsExec::ExecToStack 'cmd /c move /y "$INSTDIR\IsamAULauncher\*" "$INSTDIR\"'
  Pop $0
  nsExec::ExecToStack 'cmd /c move /y "$INSTDIR\Itch_Login_Fixer\*" "$INSTDIR\Fixer\"'
  Pop $0

  ; Clean up empty subfolders
  RMDir  "$INSTDIR\IsamAULauncher"
  RMDir  "$INSTDIR\Itch_Login_Fixer"

  ; Clean up download
  Delete "$PLUGINSDIR\IsamAU-All.zip"
  Delete "$PLUGINSDIR\7z.exe"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Start menu
  CreateDirectory "$SMPROGRAMS\${APP_SHORT}"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\${APP_SHORT}.lnk" "$INSTDIR\IsamAULauncher.exe"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\Uninstall ${APP_SHORT}.lnk" "$INSTDIR\Uninstall.exe"

  ; Uninstall registry entry
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

Section /o "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${APP_SHORT}.lnk" "$INSTDIR\IsamAULauncher.exe"
SectionEnd

;------------------------------- Component descriptions --------------------
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}    "Core launcher files (required). Downloaded from the internet."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on your Desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;------------------------------- Uninstall --------------------------------
Section "Uninstall"
  ; Start menu
  Delete "$SMPROGRAMS\${APP_SHORT}\${APP_SHORT}.lnk"
  Delete "$SMPROGRAMS\${APP_SHORT}\Uninstall ${APP_SHORT}.lnk"
  RMDir  "$SMPROGRAMS\${APP_SHORT}"

  ; Desktop
  Delete "$DESKTOP\${APP_SHORT}.lnk"

  ; Remove entire install folder
  RMDir  /r "$INSTDIR"

  ; Registry
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd
