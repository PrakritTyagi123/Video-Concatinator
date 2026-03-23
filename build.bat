@echo off
echo ============================================
echo   Video Timeline Editor - Build to EXE
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

:: Install dependencies
echo [1/3] Installing dependencies...
pip install eel pyinstaller --quiet

:: Build
echo [2/3] Building executable...
pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "VideoTimelineEditor" ^
    --add-data "web;web" ^
    --hidden-import "bottle_websocket" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --icon "NUL" ^
    main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed. Check the output above.
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo ============================================
echo   EXE is at: dist\VideoTimelineEditor.exe
echo ============================================
echo.
echo NOTE: Users still need FFmpeg installed.
echo       Install with: winget install Gyan.FFmpeg
echo.
pause
