"""
Cx_Freeze build script for CrewLauncher.
Builds both CrewLauncher and Itch_Login_Fixer into a shared lib/ folder.

Usage (from repo root):
    python build/cx_setup.py build --build-exe=dist/CrewLauncher_cx

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
        "customtkinter",
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
        ("src/launcher/resources/splash.png", "resources/splash.png"),
        ("src/launcher/resources/phosphor-icons", "resources/phosphor-icons"),
        ("src/launcher/resources/login", "resources/login"),
    ],
    "include_msvcr": True,
    "optimize": 1,
    "zip_include_packages": ["encodings", "asyncio"],
}

executables = [
    Executable(
        "src/launcher/main.py",
        base="gui",
        target_name="CrewLauncher.exe",
        icon="src/launcher/resources/icon.ico",
    ),
    Executable(
        "src/fixer/Itch_Login_Fixer.py",
        base="gui",
        target_name="Itch_Login_Fixer.exe",
        icon="src/fixer/assets/icon.ico",
    ),
]

setup(
    name="CrewLauncher",
    version="0.2",
    description="CrewLauncher - Among Us launcher with mod support",
    options={"build_exe": build_exe_options},
    executables=executables,
)
