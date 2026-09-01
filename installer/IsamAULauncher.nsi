;-------------------------------------------------------------------------------
; Isam AULauncher - NSIS installer
; Compile with: makensis.exe installer\IsamAULauncher.nsi
; Paths are resolved relative to this script, so it builds from anywhere.
;
; Packages PyInstaller --onedir output (folders with exe + _internal/).
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
!define LAUNCHER_DIR  "${ROOT}\dist\IsamAULauncher"
!define FIXER_DIR     "${ROOT}\dist\Itch_Login_Fixer"
!define SEVENZ_EXE    "${ROOT}\release\7z.exe"
!define BEPMODS_ZIP   "${ROOT}\release\bepmods.zip"

Name    "${APP_NAME}"
OutFile "${ROOT}\dist\IsamAU-Setup.exe"

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
VIAddVersionKey "FileDescription" "${APP_NAME} ${VERSION}"
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
!define MUI_WELCOMEPAGE_TEXT "A clean, modern launcher for Among Us."

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

;------------------------------- Components --------------------------------
Section "Isam AULauncher (required)" SecMain
  SectionIn RO

  ; Install entire --onedir folder to $INSTDIR
  SetOutPath "$INSTDIR"
  File /r "${LAUNCHER_DIR}\*.*"

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
  ; Install fixer into subfolder (avoids _internal/ conflict with launcher)
  SetOutPath "$INSTDIR\Fixer"
  File /r "${FIXER_DIR}\*.*"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\Itch Login Fixer.lnk" "$INSTDIR\Fixer\Itch_Login_Fixer.exe"
SectionEnd

Section "Support tools (7-zip + mods)" SecTools
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /oname=7z.exe "${SEVENZ_EXE}"
  File /oname=bepmods.zip "${BEPMODS_ZIP}"
SectionEnd

Section /o "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${APP_SHORT}.lnk" "$INSTDIR\IsamAULauncher.exe"
SectionEnd

;------------------------------- Component descriptions --------------------
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}    "Core launcher files (required)."
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
