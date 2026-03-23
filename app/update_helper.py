"""
update_helper.py — Runs as a separate process after BetterTTS exits.
Shows a themed progress window while swapping files, then relaunches.

Called by updater.py with:
    update_helper.exe <main_pid> <staging_dir> <install_dir>
"""

import sys
import os
import time
import shutil
import subprocess
import threading
from pathlib import Path


# ── Theme colors (mirrors app/gui/theme.py) ───────────────────────────────────
BG_DARK    = "#0f172a"
BG_CARD    = "#1e293b"
BG_INPUT   = "#334155"
ACCENT     = "#7c3aed"
ACCENT_HOV = "#6d28d9"
SUCCESS    = "#10b981"
SUCCESS_DIM= "#059669"
ERROR_DIM  = "#dc2626"
ERROR      = "#ef4444"
WARNING    = "#f59e0b"
TEXT       = "#e2e8f0"
TEXT_SEC   = "#94a3b8"
TEXT_DIM   = "#64748b"
SEPARATOR  = "#2d3a4f"


def get_install_dir(args):
    return Path(args[3]) if len(args) > 3 else Path(sys.executable).parent


def wait_for_process_exit(pid: int, timeout: int = 30):
    try:
        import ctypes
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return
        try:
            ctypes.windll.kernel32.WaitForSingleObject(handle, timeout * 1000)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        for _ in range(timeout * 10):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:
                return


class UpdateWindow:
    def __init__(self, install_dir: Path):
        import customtkinter as ctk
        self.ctk = ctk
        self.install_dir = install_dir

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.win = ctk.CTk()
        self.win.title("BetterTTS Updater")
        self.win.geometry("480x280")
        self.win.resizable(False, False)
        self.win.configure(fg_color=BG_DARK)
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)  # prevent close
        self.win.attributes("-topmost", True)

        # Center on screen
        self.win.update_idletasks()
        x = (self.win.winfo_screenwidth() - 480) // 2
        y = (self.win.winfo_screenheight() - 280) // 2
        self.win.geometry(f"480x280+{x}+{y}")

        # Set icon
        icon_path = install_dir / "icon.ico"
        if icon_path.exists():
            try:
                self.win.after(100, lambda: self.win.iconbitmap(str(icon_path)))
            except Exception:
                pass

        self._build_ui()

    def _build_ui(self):
        ctk = self.ctk

        # Header
        header = ctk.CTkFrame(self.win, height=56, corner_radius=0,
                               fg_color=("#1a1a2e", "#0f0f1a"))
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.place(relx=0.04, rely=0.5, anchor="w")

        ctk.CTkLabel(title_frame, text="Better",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#a78bfa").pack(side="left")
        ctk.CTkLabel(title_frame, text="TTS",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkLabel(header, text="Updater",
                     font=ctk.CTkFont(size=12),
                     text_color=TEXT_DIM).place(relx=0.96, rely=0.5, anchor="e")

        # Content
        content = ctk.CTkFrame(self.win, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # Status icon + label row
        status_row = ctk.CTkFrame(content, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 12))

        self.status_icon = ctk.CTkLabel(
            status_row, text="⬆",
            font=ctk.CTkFont(size=22),
            text_color=ACCENT, width=32,
        )
        self.status_icon.pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_row,
            text="Waiting for BetterTTS to close…",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT, anchor="w",
        )
        self.status_label.pack(side="left", padx=(8, 0))

        # Detail label
        self.detail_label = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SEC, anchor="w", justify="left",
        )
        self.detail_label.pack(fill="x", pady=(0, 14))

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            content, height=8,
            fg_color=BG_INPUT,
            progress_color=ACCENT,
            corner_radius=4,
        )
        self.progress.pack(fill="x")
        self.progress.set(0)

        # Indeterminate spinner for waiting phase
        self.progress.configure(mode="indeterminate")
        self.progress.start()

    def set_status(self, title: str, detail: str = "", color: str = TEXT,
                   icon: str = "⬆", progress: float = None):
        def _update():
            self.status_label.configure(text=title, text_color=color)
            self.status_icon.configure(text=icon, text_color=color)
            self.detail_label.configure(text=detail)
            if progress is not None:
                self.progress.stop()
                self.progress.configure(mode="determinate", progress_color=color)
                self.progress.set(progress)
            self.win.update_idletasks()
        self.win.after(0, _update)

    def set_indeterminate(self, color: str = ACCENT):
        def _update():
            self.progress.stop()
            self.progress.configure(mode="indeterminate", progress_color=color)
            self.progress.start()
        self.win.after(0, _update)

    def close_after(self, delay_ms: int = 1500):
        self.win.after(delay_ms, self.win.destroy)

    def run(self, worker_fn):
        """Start worker in background thread then run mainloop."""
        t = threading.Thread(target=worker_fn, daemon=True)
        t.start()
        self.win.mainloop()


def apply_update(main_pid: int, staging: Path, install: Path,
                 window: UpdateWindow):

    window.set_status(
        "Waiting for BetterTTS to close…",
        "Please wait while the app shuts down.",
        color=ACCENT, icon="⏳",
    )

    wait_for_process_exit(main_pid, timeout=30)
    time.sleep(1)

    window.set_status(
        "Applying update…",
        "Swapping app files with the new version.",
        color=ACCENT, icon="⬆",
    )
    window.set_indeterminate(color=ACCENT)

    try:
        steps = []

        # ── Swap app\ folder ──────────────────────────────────────────────────
        new_app = staging / "app"
        current_app = install / "app"
        if new_app.exists():
            steps.append("Updating app files…")
            window.set_status("Updating app files…", "Replacing app\\ folder.",
                              color=ACCENT, icon="⬆", progress=0.2)
            if current_app.exists():
                shutil.rmtree(current_app)
            shutil.copytree(new_app, current_app)

        # ── Swap BetterTTS.exe ────────────────────────────────────────────────
        new_exe = staging / "BetterTTS.exe"
        current_exe = install / "BetterTTS.exe"
        if new_exe.exists():
            window.set_status("Updating launcher…", "Replacing BetterTTS.exe.",
                              color=ACCENT, icon="⬆", progress=0.5)
            old_exe = install / "BetterTTS.old"
            if old_exe.exists():
                old_exe.unlink()
            if current_exe.exists():
                current_exe.rename(old_exe)
            shutil.copy2(new_exe, current_exe)

        # ── Update other files ────────────────────────────────────────────────
        window.set_status("Updating resources…", "Copying remaining files.",
                          color=ACCENT, icon="⬆", progress=0.75)

        for fname in ["requirements.txt", "version.txt"]:
            src = staging / fname
            if src.exists():
                shutil.copy2(src, install / fname)

        skip = {"app", "BetterTTS.exe", "requirements.txt", "version.txt",
                "venv", "_backup", "_update_staging", "voices", "update_helper.exe"}
        for item in staging.iterdir():
            if item.name not in skip:
                dest = install / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        # ── Clean up ──────────────────────────────────────────────────────────
        shutil.rmtree(staging, ignore_errors=True)
        old_exe = install / "BetterTTS.old"
        if old_exe.exists():
            try:
                old_exe.unlink()
            except Exception:
                pass

        # ── Success ───────────────────────────────────────────────────────────
        window.set_status(
            "Update complete!",
            "Relaunching BetterTTS…",
            color=SUCCESS, icon="✓", progress=1.0,
        )
        time.sleep(2)  # Wait for old launcher to fully exit before relaunching

        subprocess.Popen([str(current_exe)], cwd=str(install))
        window.close_after(500)

    except Exception as e:
        import traceback
        window.set_status(
            "Update failed",
            f"{e}\n\nBetterTTS will relaunch with the previous version.",
            color=ERROR, icon="✕", progress=0.0,
        )
        time.sleep(3)
        fallback = install / "BetterTTS.exe"
        if fallback.exists():
            subprocess.Popen([str(fallback)], cwd=str(install))
        window.close_after(500)


def main():
    if len(sys.argv) < 4:
        print("Usage: update_helper.exe <pid> <staging_dir> <install_dir>")
        sys.exit(1)

    main_pid  = int(sys.argv[1])
    staging   = Path(sys.argv[2])
    install   = Path(sys.argv[3])

    window = UpdateWindow(install)
    window.run(lambda: apply_update(main_pid, staging, install, window))


if __name__ == "__main__":
    main()