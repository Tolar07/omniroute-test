"""
Build script for OLP XDV Framework desktop executable.

This script uses PyInstaller to create a standalone executable
for the OLP XDV Framework desktop application.
"""

from __future__ import annotations
import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse


def get_version() -> str:
    """Get version from pyproject.toml or default."""
    try:
        import tomllib
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "0.1.0")
    except Exception:
        return "0.1.0"


def clean_build_dirs():
    """Clean previous build artifacts."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        path = Path(dir_name)
        if path.exists():
            shutil.rmtree(path)
            print(f"Cleaned {dir_name}")

    # Clean .pyc files
    for pyc_file in Path(".").rglob("*.pyc"):
        pyc_file.unlink()


def build_executable(
    name: str = "olpxdv",
    onefile: bool = True,
    console: bool = True,
    icon: str = None,
    add_data: list = None,
    hidden_imports: list = None,
    exclude_modules: list = None,
    clean: bool = True
):
    """
    Build the executable using PyInstaller.

    Args:
        name: Name of the executable
        onefile: Create a single executable file
        console: Show console window (True for CLI, False for GUI)
        icon: Path to icon file
        add_data: List of (source, dest) tuples for data files
        hidden_imports: List of hidden imports
        exclude_modules: List of modules to exclude
        clean: Clean build directories first
    """
    if clean:
        clean_build_dirs()

    # Base command
    cmd = [
        "pyinstaller",
        "--name", name,
        "--noconfirm",
    ]

    if onefile:
        cmd.append("--onefile")

    if not console:
        cmd.append("--noconsole")
    else:
        cmd.append("--console")

    if icon:
        cmd.extend(["--icon", icon])

    # Add data files
    if add_data:
        for src, dest in add_data:
            cmd.extend(["--add-data", f"{src}{os.pathsep}{dest}"])

    # Hidden imports
    if hidden_imports:
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])

    # Exclude modules
    if exclude_modules:
        for mod in exclude_modules:
            cmd.extend(["--exclude-module", mod])

    # Main script
    cmd.append("src/main.py")

    print("Running PyInstaller...")
    print("Command:", " ".join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("Build failed!")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def create_installer():
    """Create a simple installer (Windows) or package (macOS/Linux)."""
    system = sys.platform

    if system == "win32":
        # Could use NSIS or Inno Setup for Windows installer
        print("Windows installer creation not implemented yet")
    elif system == "darwin":
        # Could create .dmg for macOS
        print("macOS .dmg creation not implemented yet")
    else:
        # Could create AppImage or .deb/.rpm for Linux
        print("Linux packaging not implemented yet")


def main():
    parser = argparse.ArgumentParser(description="Build OLP XDV Framework executable")
    parser.add_argument("--name", default="olpxdv", help="Executable name")
    parser.add_argument("--no-onefile", action="store_true", help="Create directory instead of single file")
    parser.add_argument("--no-console", action="store_true", help="Hide console window (GUI mode)")
    parser.add_argument("--icon", help="Path to icon file (.ico for Windows, .icns for macOS)")
    parser.add_argument("--no-clean", action="store_true", help="Don't clean build directories first")
    parser.add_argument("--installer", action="store_true", help="Create installer after build")

    args = parser.parse_args()

    # Define data files to include
    add_data = [
        ("src/config", "config"),
        ("scripts", "scripts"),
        (".env.example", "."),
    ]

    # Hidden imports that PyInstaller might miss
    hidden_imports = [
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "watchfiles.main",
        "email.mime.text",
        "email.mime.multipart",
        "playwright.sync_api",
        "playwright.async_api",
    ]

    # Modules to exclude to reduce size
    exclude_modules = [
        "tkinter",
        "matplotlib",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "black",
        "ruff",
        "mypy",
    ]

    success = build_executable(
        name=args.name,
        onefile=not args.no_onefile,
        console=not args.no_console,
        icon=args.icon,
        add_data=add_data,
        hidden_imports=hidden_imports,
        exclude_modules=exclude_modules,
        clean=not args.no_clean
    )

    if success:
        print(f"\nExecutable created in dist/{args.name}")
        if sys.platform == "win32":
            print(f"Run with: dist\\{args.name}.exe")
        else:
            print(f"Run with: ./dist/{args.name}")

        if args.installer:
            create_installer()
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()