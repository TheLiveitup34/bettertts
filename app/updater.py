"""
updater.py — Auto-update system for BetterTTS
- Checks GitHub releases for newer versions
- Downloads and applies updates via update_helper.exe
- Crash protection via startup flag
- Auto-rollback if new version fails to start cleanly

Structure after update:
  BetterTTS.exe          <- onefile launcher (updated)
  app\                   <- source files run by venv Python (updated)
  venv\                  <- NOT updated (user's installed deps stay)
  update_helper.exe      <- NOT updated (can't replace itself)
  requirements.txt       <- updated (in case deps changed)
"""

import sys
import os
import json
import shutil
import threading
import zipfile
import tempfile
import time
from pathlib import Path
from typing import Optional, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import subprocess

GITHUB_API_URL = "https://api.github.com/repos/rubensbonc/bettertts/releases/latest"
UPDATE_CHECK_TIMEOUT = 10
STARTUP_FLAG_NAME = ".startup_in_progress"
BACKUP_DIR_NAME = "_backup"
VERSION_FILE_NAME = "version.txt"


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_current_version() -> str:
    version_file = get_base_dir() / VERSION_FILE_NAME
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"


def _parse_version(version_str: str) -> tuple:
    clean = version_str.lstrip("v").strip()
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0, 0, 0)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


# ── Crash protection ──────────────────────────────────────────────────────────

def write_startup_flag():
    flag = get_base_dir() / STARTUP_FLAG_NAME
    try:
        flag.write_text(str(time.time()))
    except Exception:
        pass


def clear_startup_flag():
    flag = get_base_dir() / STARTUP_FLAG_NAME
    try:
        if flag.exists():
            flag.unlink()
    except Exception:
        pass


def check_and_rollback() -> bool:
    base = get_base_dir()
    flag = base / STARTUP_FLAG_NAME
    backup_dir = base / BACKUP_DIR_NAME

    if not flag.exists():
        return False

    print("[Updater] Crash detected from previous launch. Checking for backup...")

    if not backup_dir.exists():
        print("[Updater] No backup found, cannot rollback.")
        try:
            flag.unlink()
        except Exception:
            pass
        return False

    print("[Updater] Rolling back to previous version...")
    try:
        _apply_rollback(base, backup_dir)
        flag.unlink()
        print("[Updater] Rollback successful.")
    except Exception as e:
        print(f"[Updater] Rollback failed: {e}")
        try:
            flag.unlink()
        except Exception:
            pass

    return True


def _apply_rollback(base: Path, backup_dir: Path):
    """Restore app\ folder and exe from backup."""
    # Restore app\ folder
    backup_app = backup_dir / "app"
    current_app = base / "app"
    if backup_app.exists():
        if current_app.exists():
            shutil.rmtree(current_app)
        shutil.copytree(backup_app, current_app)

    # Restore launcher exe
    exe_name = Path(sys.executable).name
    backup_exe = backup_dir / exe_name
    if backup_exe.exists():
        shutil.copy2(backup_exe, base / exe_name)

    # Restore requirements.txt
    backup_req = backup_dir / "requirements.txt"
    if backup_req.exists():
        shutil.copy2(backup_req, base / "requirements.txt")

    print("[Updater] Restored from backup.")


# ── Update checking ───────────────────────────────────────────────────────────

def fetch_latest_release() -> Optional[dict]:
    try:
        req = Request(
            GITHUB_API_URL,
            headers={"User-Agent": "BetterTTS-Updater", "Accept": "application/vnd.github+json"}
        )
        with urlopen(req, timeout=UPDATE_CHECK_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 404:
            print("[Updater] No releases found on GitHub.")
        else:
            print(f"[Updater] GitHub API error: {e.code}")
        return None
    except URLError as e:
        print(f"[Updater] Could not reach GitHub: {e}")
        return None
    except Exception as e:
        print(f"[Updater] Update check failed: {e}")
        return None


def find_windows_asset(release: dict) -> Optional[dict]:
    for asset in release.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and "windows" in name:
            return asset
    for asset in release.get("assets", []):
        if asset.get("name", "").lower().endswith(".zip"):
            return asset
    return None


def check_for_update() -> Optional[dict]:
    release = fetch_latest_release()
    if not release:
        return None

    latest_version = release.get("tag_name", "0.0.0")
    current_version = get_current_version()

    print(f"[Updater] Current: {current_version}  Latest: {latest_version}")

    if _is_newer(latest_version, current_version):
        asset = find_windows_asset(release)
        if asset:
            return {
                "version": latest_version,
                "asset": asset,
                "release": release,
            }

    return None


# ── Downloading & applying ────────────────────────────────────────────────────

def download_file(url: str, dest: Path, on_progress: Optional[Callable] = None):
    req = Request(url, headers={"User-Agent": "BetterTTS-Updater"})
    with urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        chunk_size = 65536
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)


def _backup_current(base: Path):
    backup_dir = base / BACKUP_DIR_NAME
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir()

    # Backup app\ folder
    app_dir = base / "app"
    if app_dir.exists():
        shutil.copytree(app_dir, backup_dir / "app")

    # Backup launcher exe (BetterTTS.exe, not sys.executable which is venv python)
    launcher = base / "BetterTTS.exe"
    if launcher.exists():
        shutil.copy2(launcher, backup_dir / "BetterTTS.exe")

    # Backup requirements.txt
    req_path = base / "requirements.txt"
    if req_path.exists():
        shutil.copy2(req_path, backup_dir / "requirements.txt")

    print(f"[Updater] Backed up to {backup_dir}")


def apply_update(zip_path: Path, on_status: Optional[Callable] = None):

    base = get_base_dir()

    def status(msg):
        print(f"[Updater] {msg}")
        if on_status:
            on_status(msg)

    status("Backing up current version...")
    _backup_current(base)

    status("Extracting update...")

    # Stage next to the exe so it's on the same drive
    staging_dir = base / "_update_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(staging_dir)

    # Unwrap single top-level folder into staging_dir directly
    items = list(staging_dir.iterdir())
    if len(items) == 1 and items[0].is_dir():
        inner = items[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(staging_dir / item.name))
        inner.rmdir()

    status("Scheduling update — closing app to apply...")

    # Find update_helper.exe next to BetterTTS.exe
    helper = base / "update_helper.exe"

    if helper.exists():
        cmd = [str(helper), str(os.getpid()), str(staging_dir), str(base)]
    else:
        # Fallback to python script for development
        helper_py = base / "app" / "update_helper.py"
        cmd = [sys.executable, str(helper_py), str(os.getpid()), str(staging_dir), str(base)]

    subprocess.Popen(
        cmd,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )


def cleanup_old_exe():
    base = get_base_dir()
    staging = base / "_update_staging"
    if staging.exists():
        try:
            shutil.rmtree(staging)
        except Exception:
            pass


# ── High level API ────────────────────────────────────────────────────────────

class Updater:
    def __init__(
        self,
        on_update_available: Optional[Callable] = None,
        on_download_progress: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        self._on_update_available = on_update_available
        self._on_download_progress = on_download_progress
        self._on_status = on_status
        self._on_error = on_error
        self._update_info: Optional[dict] = None

    def check_async(self):
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        update = check_for_update()
        if update and self._on_update_available:
            self._update_info = update
            self._on_update_available(update["version"])

    def download_and_apply(self):
        if not self._update_info:
            return

        asset = self._update_info["asset"]
        url = asset["browser_download_url"]
        version = self._update_info["version"]

        tmp_zip = Path(tempfile.mktemp(suffix=".zip", prefix="bettertts_"))
        try:
            if self._on_status:
                self._on_status(f"Downloading {version}...")

            download_file(url, tmp_zip, on_progress=self._on_download_progress)

            if self._on_status:
                self._on_status("Preparing update...")

            apply_update(tmp_zip, on_status=self._on_status)

            if self._on_status:
                self._on_status("Closing to apply update...")

            # Give UI time to show status then exit cleanly
            # update_helper will relaunch BetterTTS.exe after the swap
            time.sleep(2)
            os._exit(0)

        except Exception as e:
            print(f"[Updater] Update failed: {e}")
            if self._on_error:
                self._on_error(str(e))
        finally:
            if tmp_zip.exists():
                try:
                    tmp_zip.unlink()
                except Exception:
                    pass