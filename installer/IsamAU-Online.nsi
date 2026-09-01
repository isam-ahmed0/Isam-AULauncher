;-------------------------------------------------------------------------------
; Isam AULauncher - ONLINE NSIS installer
; Compile with: makensis.exe installer\IsamAU-Online.nsi
; Paths are resolved relative to this script, so it builds from anywhere.
;
; Downloads all files from GitHub Releases during install.
; Uses 7z.exe bundled in installer for extraction.
;-------------------------------------------------------------------------------

!include "MUI2.nsh"
!include "LogicLib.nsh"

!define APP_NAME      "Isam AULauncher"
!define APP_SHORT     "Isam AULauncher"
!define COMPANY       "Isam"
!ifndef VERSION
  !define VERSION     "0.5"
!endif
!define VERSION_DOT   "${VERSION}.0.0"

; Repo root = folder above this script (overridden by /DROOT= in build scripts)
!ifndef ROOT
  !define ROOT "${__FILEDIR__}\.."
!endif
!define SRC_ICON      "${ROOT}\src\launcher\resources\icon.ico"
!define SIDEBAR_BMP   "${ROOT}\installer\sidebar.bmp"
!define SEVENZ_EXE    "${ROOT}\release\7z.exe"

; Download URL - single zip with everything
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

  ; Download to plugins temp dir
  InitPluginsDir
  CreateDirectory "$PLUGINSDIR"

  ; Bundle 7z.exe into plugins dir for extraction
  SetOutPath "$PLUGINSDIR"
  File "/oname=7z.exe" "${SEVENZ_EXE}"

  ; Download the combined zip
  DetailPrint "Downloading files from GitHub..."
  NSISdl::download /PROGRESS "${DOWNLOAD_URL}" "$PLUGINSDIR\IsamAU-All.zip"
  Pop $0
  ${If} $0 != "success"
    MessageBox MB_ICONSTOP "Download failed. Please check your internet connection and try again.$\r$\n$\r$\nError: $0"
    Quit
  ${EndIf}

  ; Extract to temp directory
  DetailPrint "Extracting files..."
  nsExec::ExecToStack '"$PLUGINSDIR\7z.exe" x "$PLUGINSDIR\IsamAU-All.zip" -o"$PLUGINSDIR\extracted" -y'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_ICONSTOP "Extraction failed. Please try again."
    Quit
  ${EndIf}
FunctionEnd

;------------------------------- Components --------------------------------
Section "Isam AULauncher (required)" SecMain
  SectionIn RO

  ; Move extracted launcher files to install directory
  SetOutPath "$INSTDIR"
  nsExec::ExecToStack 'cmd /c xcopy /E /Y "$PLUGINSDIR\extracted\IsamAULauncher\*" "$INSTDIR\"'
  Pop $0

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

Section "Itch Login Fixer" SecFixer
  SectionIn RO
  ; Move extracted fixer files into subfolder (avoids _internal/ conflict with launcher)
  SetOutPath "$INSTDIR\Fixer"
  nsExec::ExecToStack 'cmd /c xcopy /E /Y "$PLUGINSDIR\extracted\Itch_Login_Fixer\*" "$INSTDIR\Fixer\"'
  Pop $0
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\Itch Login Fixer.lnk" "$INSTDIR\Fixer\Itch_Login_Fixer.exe"
SectionEnd

Section "Support tools (7-zip + mods)" SecTools
  SectionIn RO
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
  ; Start menu
  Delete "$SMPROGRAMS\${APP_SHORT}\${APP_SHORT}.lnk"
  Delete "$SMPROGRAMS\${APP_SHORT}\Uninstall ${APP_SHORT}.lnk"
  Delete "$SMPROGRAMS\${APP_SHORT}\Itch Login Fixer.lnk"
  RMDir  "$SMPROGRAMS\${APP_SHORT}"

  ; Desktop
  Delete "$DESKTOP\${APP_SHORT}.lnk"

  ; Remove entire install folder (launcher + fixer + all files)
  RMDir  /r "$INSTDIR"

  ; Registry
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd
