@echo off
setlocal enabledelayedexpansion

REM Always run from the folder where this script lives
cd /d "%~dp0"

echo ============================================
echo   BetterTTS - Local Build
echo ============================================
echo.

REM ── Check venv exists ──
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Please run setup.bat first!
    echo.
    pause
    exit /b 1
)

REM ── Check Python version in venv ──
echo Checking Python version...
for /f "tokens=2 delims= " %%v in ('venv\Scripts\python.exe --version 2^>^&1') do set "PYVER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if "!PY_MAJOR!" neq "3" (
    echo ERROR: Python 3.10-3.12 required, found !PYVER!
    pause
    exit /b 1
)
if !PY_MINOR! GTR 12 (
    echo ERROR: Python 3.10-3.12 required, found !PYVER!
    echo Please recreate your venv with Python 3.12.
    pause
    exit /b 1
)
echo   Found Python !PYVER! - OK
echo.

REM ── Check icon exists ──
if not exist "icon.ico" (
    echo WARNING: icon.ico not found in project root.
    echo The exe will be built without a custom icon.
    echo.
    set "ICON_FLAG="
    set "ICON_DATA="
) else (
    set "ICON_FLAG=--icon=icon.ico"
    set "ICON_DATA=--add-data "icon.ico;.""
)

REM ── Check required files exist ──
if not exist "profiles.json" (
    echo ERROR: profiles.json not found.
    pause
    exit /b 1
)
if not exist "app\launcher.py" (
    echo ERROR: app\launcher.py not found.
    pause
    exit /b 1
)
if not exist "app\update_helper.py" (
    echo ERROR: app\update_helper.py not found.
    pause
    exit /b 1
)
if not exist "requirements_build.txt" (
    echo ERROR: requirements_build.txt not found.
    pause
    exit /b 1
)

REM ── Ask for version ──
echo.
set /p "VERSION=Enter version number (e.g. 1.0.0) or press Enter to skip: "
if "!VERSION!"=="" (
    echo Skipping version file.
) else (
    echo !VERSION!> version.txt
    echo   Written version.txt = !VERSION!
)
echo.

REM ── Clean previous build ──
echo [1/5] Cleaning previous build...

REM Wipe the entire dist folder so no leftover files cause issues
if exist "dist" (
    echo   Removing dist\...
    rmdir /s /q "dist" 2>nul
    if exist "dist" (
        echo ERROR: Could not remove dist\ - is BetterTTS.exe still running?
        pause
        exit /b 1
    )
)
if exist "build" rmdir /s /q "build"
echo   Done.
echo.

REM ── Install build-only dependencies ──
REM Only installs customtkinter + pyinstaller — NOT torch or ML deps
REM Torch is installed at runtime by the setup wizard for the user's GPU
echo [2/5] Installing build dependencies (lightweight — no PyTorch)...
venv\Scripts\pip.exe install -r requirements_build.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install build dependencies.
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Build main exe ──
echo [3/5] Building BetterTTS.exe...
venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name BetterTTS ^
    !ICON_FLAG! ^
    --collect-all=customtkinter ^
    app\launcher.py

if errorlevel 1 (
    echo ERROR: PyInstaller failed building BetterTTS.exe
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Build update helper ──
echo [4/5] Building update_helper.exe...
venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --console ^
    --name update_helper ^
    app\update_helper.py

if errorlevel 1 (
    echo ERROR: PyInstaller failed building update_helper.exe
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Create output folder and move onefile exe into it ──
echo [5/5] Copying runtime files...
if not exist "dist\BetterTTS" mkdir "dist\BetterTTS"
if exist "dist\BetterTTS.exe" move /y "dist\BetterTTS.exe" "dist\BetterTTS\" >nul

copy /y "profiles.json"                        "dist\BetterTTS\" >nul
copy /y "requirements.txt"                     "dist\BetterTTS\" >nul
xcopy /e /i /y "app"                            "dist\BetterTTS\app\" >nul
copy /y "dist\update_helper.exe"               "dist\BetterTTS\" >nul
if exist "icon.ico"                            copy /y "icon.ico"                          "dist\BetterTTS\" >nul
if exist "version.txt"                         copy /y "version.txt"                       "dist\BetterTTS\" >nul
if exist "BetterTTS_Streamerbot_Import.txt"    copy /y "BetterTTS_Streamerbot_Import.txt"  "dist\BetterTTS\" >nul
if not exist "dist\BetterTTS\voices"           mkdir "dist\BetterTTS\voices"

REM ── Remove __pycache__ folders — not needed for distribution ──
for /d /r "dist\BetterTTS" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)

REM ── Remove any junk PyInstaller copied into dist that shouldn't be there ──
echo   Cleaning up PyInstaller artifacts from dist\BetterTTS\...
if exist "dist\BetterTTS\venv"          rmdir /s /q "dist\BetterTTS\venv"
if exist "dist\BetterTTS\.git"          rmdir /s /q "dist\BetterTTS\.git"
if exist "dist\BetterTTS\build"         rmdir /s /q "dist\BetterTTS\build"
if exist "dist\BetterTTS\__pycache__"   rmdir /s /q "dist\BetterTTS\__pycache__"
if exist "dist\BetterTTS\.gpu_type"     del /q "dist\BetterTTS\.gpu_type"
if exist "dist\BetterTTS\.startup_in_progress" del /q "dist\BetterTTS\.startup_in_progress"

REM ── Copy any other loose exes from dist\ into BetterTTS\ for easy testing ──
echo   Copying loose executables into dist\BetterTTS\...
for %%f in (dist\*.exe) do (
    echo     + %%~nxf
    copy /y "%%f" "dist\BetterTTS\" >nul
)
echo   Done.
echo.

REM ── Optional: zip the output ──
set /p "DO_ZIP=Zip the output? (Y/N): "
if /i "!DO_ZIP!"=="Y" (
    if "!VERSION!"=="" (
        set "ZIP_NAME=BetterTTS-windows.zip"
    ) else (
        set "ZIP_NAME=BetterTTS-windows-!VERSION!.zip"
    )
    if exist "!ZIP_NAME!" del "!ZIP_NAME!"
    echo Zipping to !ZIP_NAME!...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Compress-Archive -Path 'dist\BetterTTS\*' -DestinationPath '!ZIP_NAME!'"
    if errorlevel 1 (
        echo WARNING: Zip failed.
    ) else (
        echo   Created !ZIP_NAME!
    )
)

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\BetterTTS\BetterTTS.exe
echo.
echo   NOTE: PyTorch is NOT bundled in the exe.
echo   The setup wizard installs it at first launch
echo   with the correct CUDA version for the user's GPU.
echo ============================================
echo.

REM ── Open output folder for convenience ──
explorer "dist\BetterTTS"

pause