@echo off
setlocal
cd /d "%~dp0"

where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw main.py %*
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        python main.py %*
    ) else (
        echo [ERROR] Python was not found in PATH. Please install Python 3.
        pause
    )
)
