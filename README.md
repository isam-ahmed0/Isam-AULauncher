# Isam AULauncher

A clean, modern launcher for Among Us — maintained by **Isam**.

![image](https://github.com/isam-ahmed0/Isam-AULauncher/blob/main/Screenshot%202026-08-30%20150105.png?raw=true)

This is the continuation of my Among Us launcher project.
I changed everything, logic, language
carries the **Isam AULauncher** identity with a fresh, sleek interface.

## Install

The easiest way to use is download the IsamAULauncher-Setup-0.1.exe from [Release](https://github.com/isam-ahmed0/Isam-AULauncher/releases/download/latest)
You can also download portable zip.
Theres also a lite version which is Isam-AU-LITE.zip


## Build (Windows)

```bat
pip install -r build\requirements.txt
build\build_launcher.bat        :: IsamAULauncher.exe
build\build_bootstrapper.bat    :: IsamAULauncherBootstrapper.exe
build\build_fixer.bat           :: Itch_Login_Fixer.exe
```

Outputs land in `dist/`.

## Build the installer (NSIS)

Install the NSIS Unicode compiler from https://nsis.sourceforge.io/Download,
then:

```bat
makensis /DVERSION=0.1 installer\IsamAULauncher.nsi
```

Forked from `jogamerforgames2021/AmongUsLauncherNew` &
`jogamerforgames2021/BootstrapperTEST`. All upstream download endpoints,
Discord invite and YouTube links remain in place.
