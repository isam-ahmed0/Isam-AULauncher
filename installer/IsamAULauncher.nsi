;-------------------------------------------------------------------------------
; Isam AULauncher - NSIS installer
; Compile with: makensis.exe installer\IsamAULauncher.nsi
; Paths are resolved relative to this script, so it builds from anywhere.
;-------------------------------------------------------------------------------

!include "MUI2.nsh"
!include "LogicLib.nsh"

!define APP_NAME      "Isam AULauncher"
!define APP_SHORT     "Isam AULauncher"
!define COMPANY       "Isam"
!ifndef VERSION
  !define VERSION     "0.1"
!endif
!define VERSION_DOT   "${VERSION}.0.0"

; Repo root = folder above this script (overridden by /DROOT= in build_installer.bat)
!ifndef ROOT
  !define ROOT "${__FILEDIR__}\.."
!endif
!define SRC_ICON      "${ROOT}\src\launcher\resources\icon.ico"
!define LAUNCHER_EXE  "${ROOT}\dist\IsamAULauncher.exe"
!define FIXER_EXE     "${ROOT}\dist\Itch_Login_Fixer.exe"
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
!define MUI_FINISHPAGE_RUN "$INSTDIR\IsamAULauncher.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Run ${APP_NAME} now"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

;------------------------------- Components --------------------------------
Section "Isam AULauncher (required)" SecMain
  SectionIn RO

  SetOutPath "$INSTDIR"
  File /oname=IsamAULauncher.exe "${LAUNCHER_EXE}"
  File /oname=icon.ico "${SRC_ICON}"

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
  SetOutPath "$INSTDIR"
  File /oname=Itch_Login_Fixer.exe "${FIXER_EXE}"
  CreateShortcut "$SMPROGRAMS\${APP_SHORT}\Itch Login Fixer.lnk" "$INSTDIR\Itch_Login_Fixer.exe"
SectionEnd

Section "Support tools (7-zip + mods)" SecTools
  SetOutPath "$INSTDIR"
  File /oname=7z.exe "${SEVENZ_EXE}"
  File /oname=bepmods.zip "${BEPMODS_ZIP}"
SectionEnd

Section /o "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${APP_SHORT}.lnk" "$INSTDIR\IsamAULauncher.exe"
SectionEnd

;------------------------------- Uninstall --------------------------------
Section "Uninstall"
  ; Start menu
  Delete "$SMPROGRAMS\${APP_SHORT}\${APP_SHORT}.lnk"
  Delete "$SMPROGRAMS\${APP_SHORT}\Uninstall ${APP_SHORT}.lnk"
  Delete "$SMPROGRAMS\${APP_SHORT}\Itch Login Fixer.lnk"
  RMDir  "$SMPROGRAMS\${APP_SHORT}"

  ; Desktop
  Delete "$DESKTOP\${APP_SHORT}.lnk"

  ; Files + folder
  Delete "$INSTDIR\IsamAULauncher.exe"
  Delete "$INSTDIR\Itch_Login_Fixer.exe"
  Delete "$INSTDIR\icon.ico"
  Delete "$INSTDIR\7z.exe"
  Delete "$INSTDIR\bepmods.zip"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$INSTDIR\launcher.log"
  RMDir  /r "$INSTDIR"

  ; Registry
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd