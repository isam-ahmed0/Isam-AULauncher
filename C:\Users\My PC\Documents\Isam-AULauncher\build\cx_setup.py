"""
Cx_Freeze build script for Isam AULauncher.
Builds both IsamAULauncher and Itch_Login_Fixer into a shared lib/ folder.

Usage (from repo root):
    python build/cx_setup.py build --build-exe=dist\IsamAULauncher_cx

Requirements:
    pip install cx_Freeze>=8.7
"""
import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": [
        "PySide6",
        "requests",
        "pypresence",
        "PIL",
        "customtkinter",
        "http.server",
    ],
    "excludes": [
        "tkinter",
        "unittest",
        "test",
        "email",
        "xml",
        "html",
        "pydoc",
        "doctest",
    ],
    "include_files": [
        ("src/launcher/resources/icon.ico", "resources/icon.ico"),
    ],
    "include_msvcr": True,
    "optimize": 1,
    "zip_include_packages": ["encodings", "asyncio"],
}

executables = [
    Executable(
        "src/launcher/main.py",
        base="Win32GUI",
        target_name="IsamAULauncher.exe",
        icon="src/launcher/resources/icon.ico",
    ),
    Executable(
        "src/fixer/Itch_Login_Fixer.py",
        base="Win32GUI",
        target_name="Itch_Login_Fixer.exe",
        icon="src/fixer/assets/icon.ico",
    ),
]

setup(
    name="Isam AULauncher",
    version="0.2",
    description="Isam AULauncher - Among Us launcher with mod support",
    options={"build_exe": build_exe_options},
    executables=executables,
)
