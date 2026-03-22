@echo off
setlocal enabledelayedexpansion

REM Always run from the folder where this script lives
cd /d "%~dp0"

REM Add local sox folder to PATH if it exists (needed by Qwen-TTS)
if exist "sox" set "PATH=%CD%\sox;%PATH%"

REM Also check common install locations
if exist "C:\Program Files (x86)\sox-14-4-2" set "PATH=C:\Program Files (x86)\sox-14-4-2;%PATH%"
if exist "C:\Program Files\sox-14-4-2" set "PATH=C:\Program Files\sox-14-4-2;%PATH%"

REM CUDA compatibility — helps older GPUs (Pascal, Maxwell, Kepler)
REM Disable TF32 to avoid precision issues on older architectures
set "CUDA_TF32_OVERRIDE=0"
REM Allow CUDA to fall back gracefully instead of hard-crashing
set "CUDA_LAUNCH_BLOCKING=0"
REM Prevent cuDNN auto-tuner issues on older GPUs
set "CUBLAS_WORKSPACE_CONFIG=:16:8"

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Please run setup.bat first!
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m app.main
