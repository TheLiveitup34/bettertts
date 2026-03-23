"""
updater.py — Auto-update system for BetterTTS
- Checks GitHub releases for newer versions
- Downloads and applies updates with atomic swap
- Crash protection via startup flag
- Auto-rollback if new version fails to start cleanly
"""

import sys
import os
import json
import shutil
import hashlib
import threading
import zipfile
import tempfile
import time
from pathlib import Path
from typing import Optional, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

GITHUB_API_URL = "https://api.github.com/repos/TheLiveitup34/bettertts/releases/latest"
GITHUB_REPO_URL = "https://github.com/TheLiveitup34/bettertts"
UPDATE_CHECK_TIMEOUT = 10  # seconds

# Written on launch, deleted after clean startup — used for crash detection
STARTUP_FLAG_NAME = ".startup_in_progress"
# Folder containing backup of previous working version
BACKUP_DIR_NAME = "_backup"
# File storing the current version string
VERSION_FILE_NAME = "version.txt"


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_current_version() -> str:
    """Read version from version.txt next to the exe, fallback to 0.0.0."""
    version_file = get_base_dir() / VERSION_FILE_NAME
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"


def _parse_version(version_str: str) -> tuple:
    """Parse a version string like 'v1.2.3' or '1.2.3' into a tuple."""
    clean = version_str.lstrip("v").strip()
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0, 0, 0)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


# ── Crash protection ──────────────────────────────────────────────────────────

def write_startup_flag():
    """Call this at the very start of launch. Indicates startup is in progress."""
    flag = get_base_dir() / STARTUP_FLAG_NAME
    try:
        flag.write_text(str(time.time()))
    except Exception:
        pass


def clear_startup_flag():
    """Call this once the app has fully loaded successfully."""
    flag = get_base_dir() / STARTUP_FLAG_NAME
    try:
        if flag.exists():
            flag.unlink()
    except Exception:
        pass


def check_and_rollback() -> bool:
    """
    Check if startup flag exists from a previous run — means it crashed.
    If so, attempt rollback from backup. Returns True if rollback was performed.
    """
    base = get_base_dir()
    flag = base / STARTUP_FLAG_NAME
    backup_dir = base / BACKUP_DIR_NAME

    if not flag.exists():
        return False

    # Startup flag found — previous launch crashed before clearing it
    print("[Updater] Crash detected from previous launch. Checking for backup...")

    if not backup_dir.exists():
        print("[Updater] No backup found, cannot rollback.")
        # Clear the flag so we don't loop forever
        try:
            flag.unlink()
        except Exception:
            pass
        return False

    print("[Updater] Rolling back to previous version...")
    try:
        _apply_rollback(base, backup_dir)
        flag.unlink()
        print("[Updater] Rollback successful. Restarting...")
        # Restart the exe after rollback
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"[Updater] Rollback failed: {e}")
        try:
            flag.unlink()
        except Exception:
            pass

    return True


def _apply_rollback(base: Path, backup_dir: Path):
    """Restore _internal and exe from backup."""
    internal_dir = base / "_internal"
    exe_path = Path(sys.executable)

    # Restore _internal
    backup_internal = backup_dir / "_internal"
    if backup_internal.exists():
        if internal_dir.exists():
            shutil.rmtree(internal_dir)
        shutil.copytree(backup_internal, internal_dir)

    # Restore exe
    backup_exe = backup_dir / exe_path.name
    if backup_exe.exists():
        shutil.copy2(backup_exe, exe_path)

    print("[Updater] Restored from backup.")


# ── Update checking ───────────────────────────────────────────────────────────

def fetch_latest_release() -> Optional[dict]:
    """
    Query GitHub API for the latest release.
    Returns dict with 'tag_name' and 'assets', or None on failure.
    """
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
    """Find the Windows zip asset in a release."""
    for asset in release.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and "windows" in name:
            return asset
    # Fallback: just grab the first zip
    for asset in release.get("assets", []):
        if asset.get("name", "").lower().endswith(".zip"):
            return asset
    return None


def check_for_update() -> Optional[dict]:
    """
    Check if a newer version is available.
    Returns release dict if update available, None otherwise.
    """
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
    """Download a file with optional progress callback(bytes_done, total_bytes)."""
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
    """Back up current exe and _internal to _backup folder."""
    backup_dir = base / BACKUP_DIR_NAME
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir()

    internal_dir = base / "_internal"
    if internal_dir.exists():
        shutil.copytree(internal_dir, backup_dir / "_internal")

    exe_path = Path(sys.executable)
    if exe_path.exists():
        shutil.copy2(exe_path, backup_dir / exe_path.name)

    print(f"[Updater] Backed up current version to {backup_dir}")


def apply_update(zip_path: Path, on_status: Optional[Callable] = None):
    """
    Extract zip and swap in the new version.
    on_status(message) called with progress updates.
    """
    base = get_base_dir()

    def status(msg):
        print(f"[Updater] {msg}")
        if on_status:
            on_status(msg)

    status("Backing up current version...")
    _backup_current(base)

    status("Extracting update...")
    tmp_dir = Path(tempfile.mkdtemp(prefix="bettertts_update_"))
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        # Find the extracted root folder (zip may have a top-level folder)
        extracted_items = list(tmp_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            extracted_root = extracted_items[0]
        else:
            extracted_root = tmp_dir

        status("Applying update...")

        # Swap _internal
        new_internal = extracted_root / "_internal"
        if new_internal.exists():
            current_internal = base / "_internal"
            if current_internal.exists():
                shutil.rmtree(current_internal)
            shutil.copytree(new_internal, current_internal)

        # Swap exe
        exe_name = Path(sys.executable).name
        new_exe = extracted_root / exe_name
        if new_exe.exists():
            # On Windows we can't replace a running exe directly
            # Rename current exe to .old then copy new one in
            current_exe = Path(sys.executable)
            old_exe = current_exe.with_suffix(".old")
            if old_exe.exists():
                old_exe.unlink()
            current_exe.rename(old_exe)
            shutil.copy2(new_exe, current_exe)

        # Update version file
        new_version_file = extracted_root / VERSION_FILE_NAME
        if new_version_file.exists():
            shutil.copy2(new_version_file, base / VERSION_FILE_NAME)

        status("Update applied successfully.")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def cleanup_old_exe():
    """Remove leftover .old exe from previous update if it exists."""
    old_exe = Path(sys.executable).with_suffix(".old")
    if old_exe.exists():
        try:
            old_exe.unlink()
        except Exception:
            pass


# ── High level API ────────────────────────────────────────────────────────────

class Updater:
    """
    High-level updater. Use this in the app.

    Usage:
        updater = Updater(on_update_available=my_callback)
        updater.check_async()   # non-blocking background check
    """

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
        """Check for updates in a background thread."""
        t = threading.Thread(target=self._check_worker, daemon=True)
        t.start()

    def _check_worker(self):
        update = check_for_update()
        if update and self._on_update_available:
            self._update_info = update
            self._on_update_available(update["version"])

    def download_and_apply(self):
        """Download and apply the pending update. Call from a background thread."""
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
                self._on_status("Applying update...")

            apply_update(tmp_zip, on_status=self._on_status)

            if self._on_status:
                self._on_status("Restarting...")

            # Restart into the new version
            time.sleep(1)
            os.execv(sys.executable, [sys.executable] + sys.argv)

        except Exception as e:
            print(f"[Updater] Update failed: {e}")
            if self._on_error:
                self._on_error(str(e))
        finally:
            if tmp_zip.exists():
                tmp_zip.unlink(missing_ok=True)