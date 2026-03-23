"""
update_helper.py — Runs as a separate process after BetterTTS exits.
Waits for the main process to fully exit, then swaps in the new files
and relaunches BetterTTS.exe (the launcher).

Called by updater.py with:
    update_helper.exe <main_pid> <staging_dir> <install_dir>
"""

import sys
import os
import time
import shutil
import subprocess
from pathlib import Path

# Files and folders that should NEVER be overwritten by an update
# These contain user data that must be preserved
PRESERVE = {
    "profiles.json",
    "voices",
    "venv",
    ".gpu_type",
    "launch.log",
    "app.log",
    "model_error.log",
    "_backup",
    "_update_staging",
}


def wait_for_process_exit(pid: int, timeout: int = 30):
    """Wait for a process to exit by polling."""
    try:
        import ctypes
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return  # already gone
        try:
            ctypes.windll.kernel32.WaitForSingleObject(handle, timeout * 1000)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        # Fallback: poll manually
        for _ in range(timeout * 10):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except OSError:
                break


def apply_update(staging_dir: Path, install_dir: Path):
    """
    Swap files from staging into install_dir.
    Skips anything in PRESERVE so user data is never touched.
    """
    print(f"[UpdateHelper] Applying update from {staging_dir} to {install_dir}")

    for item in staging_dir.iterdir():
        name = item.name

        # Skip preserved files and folders
        if name in PRESERVE:
            print(f"[UpdateHelper] Skipping preserved: {name}")
            continue

        dest = install_dir / name

        try:
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                print(f"[UpdateHelper] Replaced dir: {name}")
            else:
                shutil.copy2(item, dest)
                print(f"[UpdateHelper] Replaced file: {name}")
        except Exception as e:
            print(f"[UpdateHelper] Failed to replace {name}: {e}")


def main():
    if len(sys.argv) < 4:
        print("[UpdateHelper] Usage: update_helper.exe <pid> <staging_dir> <install_dir>")
        sys.exit(1)

    main_pid    = int(sys.argv[1])
    staging_dir = Path(sys.argv[2])
    install_dir = Path(sys.argv[3])

    print(f"[UpdateHelper] Waiting for PID {main_pid} to exit...")
    wait_for_process_exit(main_pid, timeout=30)

    # Extra delay to ensure all file handles are released
    time.sleep(1)

    if not staging_dir.exists():
        print(f"[UpdateHelper] Staging dir not found: {staging_dir}")
        sys.exit(1)

    try:
        apply_update(staging_dir, install_dir)

        # Clean up staging folder
        shutil.rmtree(staging_dir, ignore_errors=True)

        print("[UpdateHelper] Update complete. Relaunching BetterTTS...")

        # Relaunch via the launcher exe — it will hand off to venv\main.py
        launcher_exe = install_dir / "BetterTTS.exe"
        if launcher_exe.exists():
            subprocess.Popen([str(launcher_exe)], cwd=str(install_dir))
        else:
            print(f"[UpdateHelper] Launcher not found: {launcher_exe}")

    except Exception as e:
        print(f"[UpdateHelper] Update failed: {e}")
        # Try to relaunch existing exe anyway so user isn't left with nothing
        launcher_exe = install_dir / "BetterTTS.exe"
        if launcher_exe.exists():
            subprocess.Popen([str(launcher_exe)], cwd=str(install_dir))
        sys.exit(1)


if __name__ == "__main__":
    main()