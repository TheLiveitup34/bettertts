import sys
import os
import socket
import atexit
import warnings
from pathlib import Path


def get_base_dir():
    """Get the real app directory whether running frozen (PyInstaller) or as a script."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


# ── SoX PATH setup (required by Qwen-TTS for voice cloning) ──
def _setup_sox():
    base = get_base_dir()
    sox_candidates = [
        base / "sox",
        Path("C:/Program Files (x86)/sox-14-4-2"),
        Path("C:/Program Files/sox-14-4-2"),
    ]
    for path in sox_candidates:
        if path.exists():
            os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")

_setup_sox()


# ── CUDA compatibility env vars (helps older GPUs: Pascal, Maxwell, Kepler) ──
os.environ.setdefault("CUDA_TF32_OVERRIDE", "0")
os.environ.setdefault("CUDA_LAUNCH_BLOCKING", "0")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":16:8")


# ── Single instance check — focus existing window if already running ──
_SINGLE_INSTANCE_PORT = 19847

def _ensure_single_instance():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        sock.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
        sock.listen(1)
        def _listen_for_focus():
            while True:
                try:
                    conn, _ = sock.accept()
                    conn.close()
                    _focus_main_window()
                except Exception:
                    break
        import threading
        t = threading.Thread(target=_listen_for_focus, daemon=True)
        t.start()
        return sock
    except OSError:
        try:
            notify = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            notify.settimeout(1.0)
            notify.connect(("127.0.0.1", _SINGLE_INSTANCE_PORT))
            notify.close()
            sys.exit(0)
        except (ConnectionRefusedError, socket.timeout, OSError):
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock2.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
                sock2.listen(1)
                def _listen_for_focus2():
                    while True:
                        try:
                            conn, _ = sock2.accept()
                            conn.close()
                            _focus_main_window()
                        except Exception:
                            break
                import threading
                t = threading.Thread(target=_listen_for_focus2, daemon=True)
                t.start()
                return sock2
            except OSError:
                return None


_main_window_ref = None

def _focus_main_window():
    global _main_window_ref
    if _main_window_ref is not None:
        try:
            _main_window_ref.after(0, lambda: (
                _main_window_ref.deiconify(),
                _main_window_ref.lift(),
                _main_window_ref.focus_force(),
            ))
        except Exception:
            pass


_socket_lock = _ensure_single_instance()

def _cleanup_socket():
    if _socket_lock is not None:
        try:
            _socket_lock.close()
        except Exception:
            pass

atexit.register(_cleanup_socket)


# ── Run setup wizard on first launch (source only, not needed in exe) ──
def _check_setup():
    # When frozen as an exe, Python and all deps are bundled — no setup needed
    if getattr(sys, 'frozen', False):
        return

    base = get_base_dir()
    gpu_file = base / ".gpu_type"
    venv_python = (
        base / "venv" / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else base / "venv" / "bin" / "python"
    )
    if not gpu_file.exists() or not venv_python.exists():
        from app.bootstrap import SetupWizard
        wizard = SetupWizard()
        wizard.mainloop()
        if venv_python.exists():
            os.execv(str(venv_python), [str(venv_python), __file__])
        else:
            sys.exit(0)

_check_setup()

# ── Crash protection — only runs after setup is confirmed complete ──
# Must be after _check_setup() so it doesn't fire on a fresh install
# Only relevant when running as a frozen exe
if getattr(sys, 'frozen', False):
    from app.updater import write_startup_flag, clear_startup_flag, check_and_rollback, cleanup_old_exe

    cleanup_old_exe()       # remove leftover .old exe from a previous update
    check_and_rollback()    # if last launch crashed, restore backup and restart
    write_startup_flag()    # mark that startup is now in progress
    atexit.register(clear_startup_flag)  # clear flag on clean exit

# Silence noisy library warnings that confuse users
warnings.filterwarnings("ignore", message=".*flash.*attn.*")
warnings.filterwarnings("ignore", message=".*flash-attn.*")
os.environ["TRANSFORMERS_NO_FLASH_ATTN_WARNING"] = "1"

# Ensure app package is importable when run as `python -m app.main`
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.gui.app_window import AppWindow


def main():
    global _main_window_ref
    app = AppWindow()
    _main_window_ref = app

    # Background update check — only runs in the packaged exe, not during development
    if getattr(sys, 'frozen', False):
        from app.updater import Updater, clear_startup_flag

        def _on_update_available(version: str):
            try:
                app.after(0, lambda: app.notify_update_available(version))
            except Exception:
                pass

        updater = Updater(on_update_available=_on_update_available)
        updater.check_async()
        app.updater = updater

        # Mark startup as successful — clears the crash protection flag
        clear_startup_flag()

    app.mainloop()


if __name__ == "__main__":
    main()