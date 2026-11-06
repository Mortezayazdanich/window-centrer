"""
Build script to compile Window Centerer into a standalone single-file Windows executable (.exe).
Run: python build_exe.py
"""

import os
import subprocess
import sys

def build():
    print("=== Window Centerer Standalone Executable Builder ===")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"Found PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller is not currently installed.")
        print("To build the standalone .exe, install PyInstaller:")
        print("    pip install pyinstaller")
        print("\nThen run this script again:")
        print("    python build_exe.py")
        sys.exit(1)

    icon_path = os.path.abspath("assets/icon.ico")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "WindowCenterer",
        f"--icon={icon_path}",
        "--add-data", f"assets{os.pathsep}assets",
        "main.py"
    ]

    print("\nRunning PyInstaller build command:")
    print(" ".join(cmd))
    res = subprocess.run(cmd)

    if res.returncode == 0:
        exe_path = os.path.abspath("dist/WindowCenterer.exe")
        print("\n[SUCCESS] Build completed successfully!")
        print(f"Standalone executable created at:\n  {exe_path}")
    else:
        print("\n[FAILED] Build failed with return code:", res.returncode)

if __name__ == "__main__":
    build()
