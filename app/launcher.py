"""
launcher.py — Lightweight entry point bundled by PyInstaller.

Only imports standard library + customtkinter (for the setup wizard).
Never imports torch, numpy, fastapi, or any ML dependency.

On first launch: runs the setup wizard to create the venv + install deps.
On subsequent launches: immediately hands off to venv\Scripts\python.exe
which runs main.py with the full ML stack available.
"""

import sys
import os
import socket
import atexit
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


# ── SoX PATH setup ───────────────────────────────────────────────────────────
def _setup_sox():
    base = get_base_dir()
    for path in [
        base / "sox",
        Path("C:/Program Files (x86)/sox-14-4-2"),
        Path("C:/Program Files/sox-14-4-2"),
    ]:
        if path.exists():
            os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")

_setup_sox()


# ── Launcher single instance — separate port from the app ────────────────────
# This only prevents two launchers running at once (e.g. double-click during setup)
# The app uses port 19847. The launcher uses 19848. Completely independent.
_LAUNCHER_PORT = 19848

def _ensure_single_launcher():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind(("127.0.0.1", _LAUNCHER_PORT))
        sock.listen(1)
        return sock
    except OSError:
        # Another launcher is already running — just exit silently
        sys.exit(0)

_launcher_lock = _ensure_single_launcher()

def _release_launcher_lock():
    try:
        _launcher_lock.close()
    except Exception:
        pass

atexit.register(_release_launcher_lock)


# ── Launch app ────────────────────────────────────────────────────────────────
def _launch_app(venv_python, main_py):
    """
    Launch the full app via venv Python without showing any console window.
    Writes a launch.log next to the exe for debugging startup failures.
    """
    import subprocess
    import time
    import tkinter as tk
    from tkinter import messagebox

    base = get_base_dir()
    log_path = base / "launch.log"

    def log(msg):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    log("=== Launch attempt ===")
    log(f"venv_python: {venv_python}")
    log(f"main_py: {main_py}")
    log(f"main_py exists: {main_py.exists()}")
    log(f"venv_python exists: {Path(venv_python).exists()}")
    log(f"cwd: {main_py.parent.parent}")
    log(f"cwd exists: {main_py.parent.parent.exists()}")

    if not Path(venv_python).exists():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Launch Error",
            f"venv Python not found:\n{venv_python}\n\n"
            f"Delete the venv\\ folder and relaunch to reinstall."
        )
        root.destroy()
        sys.exit(1)

    if not main_py.exists():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Launch Error",
            f"app\\main.py not found:\n{main_py}\n\n"
            f"Please reinstall BetterTTS."
        )
        root.destroy()
        sys.exit(1)

    NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    proc = subprocess.Popen(
        [str(venv_python), str(main_py)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=NO_WINDOW,
        cwd=str(main_py.parent.parent),
    )

    log(f"Process started with PID: {proc.pid}")

    # Release the launcher lock now so the app can start cleanly
    # without any port conflicts on its own instance check (port 19847)
    _release_launcher_lock()

    # Wait up to 10 seconds — if the process exits in that window it crashed
    for _ in range(100):
        time.sleep(0.1)
        if proc.poll() is not None:
            _, stderr = proc.communicate()
            error_msg = stderr.strip() if stderr else "No error output captured"
            log(f"Process exited early with code {proc.returncode}")
            log(f"stderr: {error_msg}")
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "BetterTTS Failed to Start",
                f"BetterTTS exited unexpectedly (code {proc.returncode}).\n\n"
                f"Error:\n{error_msg[-1000:]}\n\n"
                f"Check launch.log next to BetterTTS.exe for details.\n"
                f"Try deleting the venv\\ folder and relaunching to reinstall."
            )
            root.destroy()
            sys.exit(1)

    log("Process still running after 10s — launcher exiting cleanly")
    sys.exit(0)


# ── Setup wizard + venv handoff ───────────────────────────────────────────────
def _check_setup():
    base = get_base_dir()
    gpu_file = base / ".gpu_type"
    venv_python = (
        base / "venv" / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else base / "venv" / "bin" / "python"
    )
    main_py = base / "app" / "main.py"

    if not gpu_file.exists() or not venv_python.exists():
        from app.bootstrap import SetupWizard
        wizard = SetupWizard()
        wizard.mainloop()
        if venv_python.exists():
            _launch_app(venv_python, main_py)
        else:
            sys.exit(0)
    else:
        _launch_app(venv_python, main_py)


if __name__ == "__main__":
    _check_setup()