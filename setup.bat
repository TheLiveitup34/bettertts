@echo off
setlocal enabledelayedexpansion

REM Always run from the folder where this script lives
cd /d "%~dp0"

echo ============================================
echo   BetterTTS - First Time Setup
echo ============================================
echo.
echo   IMPORTANT: BetterTTS requires SoX for voice cloning.
echo   If you haven't installed it yet, please download it from:
echo   https://sox.sourceforge.net
echo.
set /p "SOX_CONFIRM=  Have you installed SoX or want to continue without it? (Y/N): "
if /i "!SOX_CONFIRM!" neq "Y" (
    echo.
    echo   Please install SoX first, then run setup.bat again.
    echo.
    pause
    exit /b 0
)
echo.

REM ── Find a compatible Python (3.10, 3.11, or 3.12) ──
REM PyTorch does NOT have wheels for Python 3.13+ yet, so we must use 3.12 or older.
set "PY_CMD="

REM First check if 'python' on PATH is already a compatible version
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER_CHECK=%%v"
    for /f "tokens=1,2 delims=." %%a in ("!PYVER_CHECK!") do (
        set "PY_MAJOR=%%a"
        set "PY_MINOR=%%b"
    )
    if "!PY_MAJOR!"=="3" (
        if !PY_MINOR! LEQ 12 if !PY_MINOR! GEQ 10 (
            set "PY_CMD=python"
            echo   Found compatible Python !PYVER_CHECK!
            goto :python_ready
        )
    )
    echo   Found Python !PYVER_CHECK! but it is NOT compatible with PyTorch.
    echo   PyTorch requires Python 3.10, 3.11, or 3.12.
)

REM Check if Python 3.12 is installed via the py launcher
py -3.12 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3.12"
    for /f "tokens=2 delims= " %%v in ('py -3.12 --version 2^>^&1') do set "PYVER_CHECK=%%v"
    echo   Found Python !PYVER_CHECK! via py launcher
    goto :python_ready
)

REM Check 3.11 as fallback
py -3.11 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3.11"
    for /f "tokens=2 delims= " %%v in ('py -3.11 --version 2^>^&1') do set "PYVER_CHECK=%%v"
    echo   Found Python !PYVER_CHECK! via py launcher
    goto :python_ready
)

REM Check 3.10 as fallback
py -3.10 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3.10"
    for /f "tokens=2 delims= " %%v in ('py -3.10 --version 2^>^&1') do set "PYVER_CHECK=%%v"
    echo   Found Python !PYVER_CHECK! via py launcher
    goto :python_ready
)

REM No compatible Python found — install 3.12
echo   No compatible Python found. Installing Python 3.12...
echo.

set "PY_INSTALLER=%TEMP%\python-3.12-installer.exe"
set "PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"

echo   Downloading Python 3.12 installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PY_URL!' -OutFile '!PY_INSTALLER!'"

if not exist "!PY_INSTALLER!" (
    echo.
    echo   ERROR: Failed to download Python installer.
    echo   Please install Python 3.12 manually from https://www.python.org/downloads/release/python-3128/
    echo   Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo   Installing Python 3.12 (this may take a minute)...
echo   Python will be added to PATH automatically.
echo.

REM /quiet = no UI, InstallAllUsers=0 = current user only, PrependPath=1 = add to PATH
"!PY_INSTALLER!" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
if !errorlevel! neq 0 (
    echo.
    echo   Silent install failed. Opening interactive installer...
    echo   IMPORTANT: Check "Add Python to PATH" at the bottom of the installer!
    echo.
    "!PY_INSTALLER!"
)

del "!PY_INSTALLER!" 2>nul

REM Refresh PATH so we can find the newly installed Python
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
set "PATH=!USER_PATH!;%PATH%"

REM Try the freshly installed Python
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
    goto :python_ready
)

py -3.12 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3.12"
    goto :python_ready
)

echo.
echo   ERROR: Python still not found after installation.
echo   Please close this window, open a NEW command prompt, and run setup.bat again.
echo.
pause
exit /b 1

:python_ready

for /f "tokens=2 delims= " %%v in ('!PY_CMD! --version 2^>^&1') do set "PYVER=%%v"
echo   Python version: %PYVER%

echo.
echo [1/5] Creating virtual environment...
if exist "venv" (
    echo   Virtual environment already exists, reusing it.
) else (
    !PY_CMD! -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)
call venv\Scripts\activate.bat

echo.
echo [2/5] Detecting GPU...

REM Detect GPU using PowerShell (reliable on modern Windows 10/11)
REM -NoProfile bypasses user profile scripts, -ExecutionPolicy Bypass avoids policy blocks
set "GPU_TYPE=cpu"
set "GPU_NAME=None detected"

REM Get all GPU names into a temp file for reliable parsing
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance -ClassName Win32_VideoController | Select-Object -ExpandProperty Name" > "%TEMP%\bettertts_gpus.txt" 2>nul

REM Check for NVIDIA first (highest priority - any NVIDIA GPU supports CUDA)
REM Matches: GeForce RTX/GTX, Quadro, Tesla, NVIDIA T-series, etc.
findstr /i "NVIDIA GeForce Quadro Tesla" "%TEMP%\bettertts_gpus.txt" >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('findstr /i "NVIDIA GeForce Quadro Tesla" "%TEMP%\bettertts_gpus.txt"') do (
        set "GPU_TYPE=nvidia"
        set "GPU_NAME=%%i"
    )
    goto :gpu_done
)

REM Check for ANY AMD/ATI GPU (discrete or integrated)
REM Matches: Radeon RX, Radeon Pro, Radeon Vega, Radeon Graphics, ATI, etc.
findstr /i "Radeon AMD ATI" "%TEMP%\bettertts_gpus.txt" >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('findstr /i "Radeon AMD ATI" "%TEMP%\bettertts_gpus.txt"') do (
        set "GPU_TYPE=amd"
        set "GPU_NAME=%%i"
    )
    goto :gpu_done
)

REM Check for ANY Intel GPU (Arc discrete, Iris, UHD, HD Graphics)
REM Matches: Intel Arc, Intel Iris, Intel UHD, Intel HD Graphics
findstr /i "Intel" "%TEMP%\bettertts_gpus.txt" >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('findstr /i "Intel" "%TEMP%\bettertts_gpus.txt"') do (
        set "GPU_TYPE=intel"
        set "GPU_NAME=%%i"
    )
    goto :gpu_done
)

:gpu_done
del "%TEMP%\bettertts_gpus.txt" 2>nul

echo.
echo   Detected: !GPU_NAME!
echo   Backend:  !GPU_TYPE!
echo.

REM Install PyTorch based on detected GPU
if "!GPU_TYPE!"=="nvidia" goto :install_nvidia
goto :skip_nvidia

:install_nvidia
echo   NVIDIA GPU detected: !GPU_NAME!

echo.
echo   Installing PyTorch with CUDA 11.8 (supports ALL NVIDIA GPUs)
echo   Compatible with: GTX 600/700/900/1000/1600, RTX 2000/3000/4000/5000 series
echo   This downloads ~2.5 GB on first install, may take several minutes.
echo.
pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
if errorlevel 1 (
    echo.
    echo   WARNING: CUDA 11.8 install failed. Trying CUDA 12.4...
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    if errorlevel 1 (
        echo.
        echo   WARNING: All CUDA installs failed. Falling back to CPU-only PyTorch.
        pip install --no-cache-dir torch torchvision torchaudio
    )
)

REM Verify CUDA actually works with this GPU
python -c "import torch; assert torch.cuda.is_available(), 'no cuda'; print('  CUDA test: OK - ' + torch.cuda.get_device_name(0))" 2>nul
if !errorlevel! neq 0 (
    echo.
    echo   WARNING: CUDA installed but not detected at runtime.
    echo   This can happen if NVIDIA drivers are outdated.
    echo   Please update your NVIDIA drivers from: https://www.nvidia.com/download/index.aspx
    echo   TTS will still work on CPU in the meantime.
)
goto :pytorch_done

:skip_nvidia

if "!GPU_TYPE!"=="amd" (
    echo   AMD GPU detected.
    echo   NOTE: AMD GPUs on Windows do not have full PyTorch GPU support.
    echo   Installing CPU PyTorch. TTS will work but will be slower than NVIDIA CUDA.
    echo   For best performance, an NVIDIA GPU is recommended.
    echo.
    pip install --no-cache-dir torch torchvision torchaudio
    goto :pytorch_done
)

if "!GPU_TYPE!"=="intel" (
    echo   Intel Arc GPU detected.
    echo   NOTE: Intel GPUs on Windows have limited PyTorch support.
    echo   Installing CPU PyTorch. TTS will work but will be slower than NVIDIA CUDA.
    echo.
    pip install --no-cache-dir torch torchvision torchaudio
    goto :pytorch_done
)

REM Fallback: no dedicated GPU
echo   No dedicated GPU detected (integrated graphics only).
echo   Installing CPU-only PyTorch. TTS will work but generation will be slower.
echo   For best performance, an NVIDIA GPU (RTX 3060+) is recommended.
echo.
pip install --no-cache-dir torch torchvision torchaudio

:pytorch_done

echo.
echo [3/5] Installing BetterTTS dependencies...
pip install --no-cache-dir -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [4/5] Creating voices directory...
if not exist "voices" mkdir voices

echo.
echo [5/5] Saving configuration...
echo !GPU_TYPE!> .gpu_type

echo.
echo ============================================
echo   Setup complete!
echo.
echo   GPU: !GPU_NAME!
echo   Backend: !GPU_TYPE!
echo.
if "!GPU_TYPE!"=="nvidia" (
    echo   NVIDIA GPU with CUDA - you'll get the best performance!
)
if "!GPU_TYPE!"=="amd" (
    echo   AMD GPU detected - will run on CPU.
    echo   Qwen3-TTS requires NVIDIA CUDA for GPU acceleration.
    echo   TTS will work fine, just slower than on an NVIDIA card.
)
if "!GPU_TYPE!"=="intel" (
    echo   Intel GPU detected - will run on CPU.
    echo   Qwen3-TTS requires NVIDIA CUDA for GPU acceleration.
    echo   TTS will work fine, just slower than on an NVIDIA card.
)
if "!GPU_TYPE!"=="cpu" (
    echo   No GPU detected - will run on CPU.
    echo   TTS will work, but for faster generation consider an NVIDIA GPU.
)
echo.
echo   Run start.bat to launch BetterTTS.
echo.
echo   On first launch, the app will download the AI model
echo   (~2.5-4.5 GB depending on your choice). One-time only.
echo ============================================
echo.
pause
