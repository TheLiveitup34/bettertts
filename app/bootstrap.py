import sys
import os
import subprocess
import threading
import platform
import tkinter as tk

# ── Python version check — only relevant when running from source ──
if not getattr(sys, 'frozen', False):
    def _check_python_version():
        try:
            from app.constants import SUPPORTED_PYTHON_VERSIONS
            compatible = [tuple(v) for v in SUPPORTED_PYTHON_VERSIONS]
        except ImportError:
            # Fallback if constants isn't importable yet
            compatible = [(3, 10), (3, 11), (3, 12)]

        major, minor = sys.version_info.major, sys.version_info.minor
        if (major, minor) not in compatible:
            versions_str = ", ".join(f"{ma}.{mi}" for ma, mi in compatible)
            root = tk.Tk()
            root.withdraw()
            from tkinter import messagebox
            messagebox.showerror(
                "Wrong Python Version",
                f"BetterTTS requires Python {versions_str}.\n\n"
                f"You are running Python {major}.{minor}.\n\n"
                f"Please download a compatible version from:\n"
                f"https://www.python.org/downloads/"
            )
            root.destroy()
            sys.exit(1)

    _check_python_version()

# ── Bootstrap: ensure customtkinter is available before importing it ──
# Only needed when running from source — frozen exe has it bundled already
if not getattr(sys, 'frozen', False):
    def bootstrap_ctk():
        try:
            import customtkinter
            return True
        except ImportError:
            pass
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter", "--quiet"])
            return True
        except Exception:
            return False

    if not bootstrap_ctk():
        root = tk.Tk()
        root.withdraw()
        from tkinter import messagebox
        messagebox.showerror("Setup Error", "Could not install customtkinter.\nPlease run: pip install customtkinter")
        sys.exit(1)

import customtkinter as ctk
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────

def get_base_dir():
    """Get the real app directory whether running frozen (PyInstaller) or as a script."""
    if getattr(sys, 'frozen', False):
        return str(Path(sys.executable).parent)
    else:
        return str(Path(__file__).parent.parent)

BASE_DIR = get_base_dir()

# On Windows, prevent any subprocess from opening a visible console window
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


def run(cmd, **kwargs):
    """Run a shell command and return (returncode, stdout+stderr combined)."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=_NO_WINDOW,
        **kwargs
    )
    return result.returncode, result.stdout


def run_stream(cmd, on_line, **kwargs):
    """
    Run a command and call on_line(line) in real time as output arrives.
    Returns returncode. Use this for long-running installs so the log
    updates live instead of waiting for the process to finish.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=_NO_WINDOW,
        **kwargs
    )
    for line in proc.stdout:
        on_line(line)
    proc.wait()
    return proc.returncode

def detect_gpu():
    """Return (gpu_type, gpu_name) where gpu_type is nvidia/amd/intel/cpu."""
    if platform.system() != "Windows":
        return "cpu", "Non-Windows platform"

    rc, out = run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", "Get-CimInstance -ClassName Win32_VideoController | Select-Object -ExpandProperty Name"],
    )
    lines = out.strip().splitlines()

    for line in lines:
        l = line.lower()
        if any(k in l for k in ["nvidia", "geforce", "quadro", "tesla"]):
            return "nvidia", line.strip()
    for line in lines:
        l = line.lower()
        if any(k in l for k in ["radeon", "amd", "ati"]):
            return "amd", line.strip()
    for line in lines:
        if "intel" in line.lower():
            return "intel", line.strip()

    return "cpu", "None detected"

def is_blackwell(gpu_name):
    for token in ["5060", "5070", "5080", "5090", "B100", "B200", "GB200", "GB300"]:
        if token in gpu_name:
            return True
    return False

def find_venv_python():
    candidates = [
        os.path.join(BASE_DIR, "venv", "Scripts", "python.exe"),
        os.path.join(BASE_DIR, "venv", "bin", "python"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def find_venv_pip():
    candidates = [
        os.path.join(BASE_DIR, "venv", "Scripts", "pip.exe"),
        os.path.join(BASE_DIR, "venv", "bin", "pip"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

# ────────────────────────────────────────────────────────────────────────────────
# Main Setup Window
# ────────────────────────────────────────────────────────────────────────────────

class SetupWizard(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("BetterTTS — First Time Setup")
        self.geometry("700x540")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._setup_thread = None
        self._cancelled = False

        self._build_ui()
        self._show_step_welcome()

    # ── UI skeleton ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color=("#1a1a2e", "#0f0f1a"))
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="BetterTTS Setup",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#4fc3f7"
        ).place(relx=0.04, rely=0.5, anchor="w")

        self._step_label = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(size=12),
            text_color="#888"
        )
        self._step_label.place(relx=0.96, rely=0.5, anchor="e")

        # Content area
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=30, pady=20)

        # Progress bar (hidden until install starts)
        self._progress = ctk.CTkProgressBar(self, height=6, corner_radius=0)
        self._progress.pack(fill="x", side="bottom")
        self._progress.set(0)
        self._progress.pack_forget()

        # Log box (hidden until install starts)
        self._log_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("#0d0d0d", "#0d0d0d"), height=140)
        self._log_frame.pack(fill="x", side="bottom")
        self._log_frame.pack_forget()
        self._log_frame.pack_propagate(False)

        self._log = ctk.CTkTextbox(
            self._log_frame, font=ctk.CTkFont(family="Courier New", size=11),
            fg_color="#0d0d0d", text_color="#a0e0a0", wrap="word",
            border_width=0
        )
        self._log.pack(fill="both", expand=True, padx=6, pady=4)

    def _clear_content(self):
        for w in self._content.winfo_children():
            w.destroy()

    def _set_step(self, text):
        self._step_label.configure(text=text)

    # ── Step 1: Welcome / SoX confirmation ───────────────────────────────────

    def _show_step_welcome(self):
        self._clear_content()
        self._set_step("Step 1 of 4")

        ctk.CTkLabel(
            self._content,
            text="Welcome to BetterTTS",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            self._content,
            text="This wizard will set up your environment, detect your GPU,\nand install all required dependencies.",
            font=ctk.CTkFont(size=13),
            text_color="#aaa",
            justify="left"
        ).pack(anchor="w", pady=(0, 20))

        # SoX notice
        sox_frame = ctk.CTkFrame(self._content, fg_color=("#1e2a38", "#1e2a38"), corner_radius=8)
        sox_frame.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            sox_frame,
            text="⚠  Voice Cloning requires SoX",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffcc44"
        ).pack(anchor="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            sox_frame,
            text="Download SoX from  https://sox.sourceforge.net\n"
                 "Install it before setup if you want to use voice cloning.\n"
                 "You can also continue without it — only cloning will be unavailable.",
            font=ctk.CTkFont(size=12),
            text_color="#ccc",
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        self._sox_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self._content,
            text="I have installed SoX (or I don't need voice cloning right now)",
            variable=self._sox_var,
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", pady=(0, 24))

        ctk.CTkButton(
            self._content,
            text="Next →",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=140, height=38,
            command=self._on_welcome_next
        ).pack(anchor="e")

    def _on_welcome_next(self):
        if not self._sox_var.get():
            from tkinter import messagebox
            messagebox.showwarning(
                "SoX Required",
                "Please install SoX from https://sox.sourceforge.net\n"
                "then check the box to continue.\n\n"
                "Or check the box to continue without voice cloning."
            )
            return
        self._show_step_gpu()

    # ── Step 2: GPU detection ─────────────────────────────────────────────────

    def _show_step_gpu(self):
        self._clear_content()
        self._set_step("Step 2 of 4")

        ctk.CTkLabel(
            self._content,
            text="Detecting Your GPU",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 8))

        detecting_label = ctk.CTkLabel(
            self._content,
            text="Scanning hardware…",
            font=ctk.CTkFont(size=13),
            text_color="#aaa"
        )
        detecting_label.pack(anchor="w")

        spinner = ctk.CTkProgressBar(self._content, mode="indeterminate", height=4)
        spinner.pack(fill="x", pady=(10, 0))
        spinner.start()

        self._gpu_result_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        self._gpu_result_frame.pack(fill="x", pady=(16, 0))

        def do_detect():
            gpu_type, gpu_name = detect_gpu()
            self.after(0, lambda: self._on_gpu_detected(gpu_type, gpu_name, detecting_label, spinner))

        threading.Thread(target=do_detect, daemon=True).start()

    def _on_gpu_detected(self, gpu_type, gpu_name, detecting_label, spinner):
        spinner.stop()
        spinner.destroy()
        detecting_label.configure(text="Detection complete.")

        colors = {
            "nvidia": ("#1a3a1a", "#66bb6a", "NVIDIA CUDA — best performance"),
            "amd":    ("#3a2a1a", "#ffa726", "AMD — will run on CPU (no CUDA support on Windows)"),
            "intel":  ("#1a2a3a", "#42a5f5", "Intel — will run on CPU"),
            "cpu":    ("#2a2a2a", "#aaa",    "No dedicated GPU — will run on CPU"),
        }
        bg, accent, note = colors.get(gpu_type, colors["cpu"])

        card = ctk.CTkFrame(self._gpu_result_frame, fg_color=(bg, bg), corner_radius=8)
        card.pack(fill="x")

        ctk.CTkLabel(
            card,
            text=gpu_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=accent
        ).pack(anchor="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            card,
            text=note,
            font=ctk.CTkFont(size=12),
            text_color="#ccc"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        self._detected_gpu_type = gpu_type
        self._detected_gpu_name = gpu_name

        ctk.CTkButton(
            self._gpu_result_frame,
            text="Next →",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=140, height=38,
            command=self._show_step_venv
        ).pack(anchor="e", pady=(16, 0))

    # ── Step 3: Venv + install ────────────────────────────────────────────────

    def _show_step_venv(self):
        self._clear_content()
        self._set_step("Step 3 of 4")

        ctk.CTkLabel(
            self._content,
            text="Installing Dependencies",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 6))

        self._status_label = ctk.CTkLabel(
            self._content,
            text="Starting…",
            font=ctk.CTkFont(size=13),
            text_color="#4fc3f7"
        )
        self._status_label.pack(anchor="w", pady=(0, 10))

        self._task_labels = {}
        tasks = [
            ("python",  "Install Python 3.12 (if needed)"),
            ("venv",    "Create virtual environment"),
            ("torch",   "Install PyTorch"),
            ("deps",    "Install BetterTTS dependencies"),
            ("voices",  "Create voices directory"),
            ("config",  "Save configuration"),
        ]
        for key, label in tasks:
            row = ctk.CTkFrame(self._content, fg_color="transparent")
            row.pack(fill="x", pady=1)
            icon = ctk.CTkLabel(row, text="○", font=ctk.CTkFont(size=13), text_color="#555", width=20)
            icon.pack(side="left")
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12), text_color="#999").pack(side="left", padx=6)
            self._task_labels[key] = icon

        # Show log + progress
        self._log_frame.pack(fill="x", side="bottom")
        self._progress.pack(fill="x", side="bottom")
        self._progress.set(0)

        self._setup_thread = threading.Thread(target=self._run_install, daemon=True)
        self._setup_thread.start()

    def _set_task(self, key, state):
        """state: pending / running / done / error"""
        icons = {"pending": ("○", "#555"), "running": ("◉", "#4fc3f7"), "done": ("✓", "#66bb6a"), "error": ("✗", "#ef5350")}
        icon, color = icons.get(state, icons["pending"])
        if key in self._task_labels:
            self._task_labels[key].configure(text=icon, text_color=color)

    def _log_write(self, text):
        self.after(0, lambda: (
            self._log.insert("end", text),
            self._log.see("end")
        ))

    def _set_status(self, text, color="#4fc3f7"):
        self.after(0, lambda: self._status_label.configure(text=text, text_color=color))

    def _set_progress(self, value):
        self.after(0, lambda: self._progress.set(value))

    # ── The actual install logic (runs in thread) ─────────────────────────────

    def _find_system_python(self):
        """
        Find a compatible system Python (3.10-3.12) to create the venv with.
        If none is found, automatically downloads and installs Python 3.12.
        When running as a frozen exe sys.executable is BetterTTS.exe, not Python,
        so we must locate the real Python interpreter explicitly.
        """
        import shutil
        from app.constants import SUPPORTED_PYTHON_VERSIONS

        # Try py launcher first (most reliable on Windows)
        py = shutil.which("py")
        if py:
            for major, minor in reversed(SUPPORTED_PYTHON_VERSIONS):
                rc, out = run([py, f"-{major}.{minor}", "--version"])
                if rc == 0:
                    self._log_write(f"Found Python {major}.{minor} via py launcher\n")
                    return [py, f"-{major}.{minor}"]

        # Try python3.12, python3.11, python3.10 directly on PATH
        for major, minor in reversed(SUPPORTED_PYTHON_VERSIONS):
            name = f"python{major}.{minor}" if sys.platform != "win32" else "python"
            found = shutil.which(name)
            if found:
                rc, out = run([found, "--version"])
                if rc == 0 and f"{major}.{minor}" in out:
                    self._log_write(f"Found {found}\n")
                    return [found]

        # Try plain python/python3 and check version
        for candidate in ["python3", "python"]:
            found = shutil.which(candidate)
            if found:
                rc, out = run([found, "--version"])
                if rc == 0:
                    for major, minor in SUPPORTED_PYTHON_VERSIONS:
                        if f"{major}.{minor}" in out:
                            self._log_write(f"Found {found} ({out.strip()})\n")
                            return [found]

        # No compatible Python found — download and install Python 3.12 automatically
        self._log_write("\nNo compatible Python found. Downloading Python 3.12...\n")
        self._set_status("Downloading Python 3.12…")
        result = self._download_and_install_python()
        if result:
            return result
        return None

    def _download_and_install_python(self):
        """
        Download the Python 3.12 installer from python.org and install silently.
        Returns the python command list if successful, None otherwise.
        """
        import shutil
        import tempfile
        import urllib.request

        PY_URL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        PY_VERSION = "3.12"

        tmp_dir = tempfile.mkdtemp(prefix="bettertts_py_")
        installer = os.path.join(tmp_dir, "python-3.12-installer.exe")

        try:
            # Download with progress
            self._log_write(f"Downloading from {PY_URL}\n")

            def _report(block, block_size, total):
                if total > 0:
                    done = block * block_size
                    pct = min(done / total * 100, 100)
                    mb_done = done / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    self._set_status(f"Downloading Python 3.12… {mb_done:.1f}/{mb_total:.1f} MB ({pct:.0f}%)")

            urllib.request.urlretrieve(PY_URL, installer, reporthook=_report)
            self._log_write("Download complete. Installing Python 3.12...\n")
            self._set_status("Installing Python 3.12…")

            # Silent install — current user only, add to PATH, include py launcher
            rc, out = run([
                installer,
                "/quiet",
                "InstallAllUsers=0",
                "PrependPath=1",
                "Include_test=0",
                "Include_launcher=1",
            ])
            self._log_write(out or "(no output)\n")

            if rc != 0:
                self._log_write(f"Installer exited with code {rc}\n")
                return None

            self._log_write("Python 3.12 installed.\n")

            # Refresh PATH in current process so we can find the new python
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                    user_path, _ = winreg.QueryValueEx(key, "Path")
                    os.environ["PATH"] = user_path + os.pathsep + os.environ.get("PATH", "")
            except Exception:
                pass

            # Try py launcher first after install
            py = shutil.which("py")
            if py:
                rc, out = run([py, f"-{PY_VERSION}", "--version"])
                if rc == 0:
                    self._log_write(f"Python {PY_VERSION} ready via py launcher\n")
                    return [py, f"-{PY_VERSION}"]

            # Try direct python path
            for candidate in [f"python{PY_VERSION}", "python3", "python"]:
                found = shutil.which(candidate)
                if found:
                    rc, out = run([found, "--version"])
                    if rc == 0 and PY_VERSION in out:
                        self._log_write(f"Python {PY_VERSION} ready at {found}\n")
                        return [found]

            self._log_write("Python installed but not found on PATH yet.\n")
            self._log_write("Please close and reopen BetterTTS to complete setup.\n")
            return None

        except Exception as e:
            self._log_write(f"Failed to download/install Python: {e}\n")
            return None
        finally:
            try:
                import shutil as _shutil
                _shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    def _run_install(self):
        steps = 6
        step = 0

        # 1. Find / install Python
        self.after(0, lambda: self._set_task("python", "running"))
        self._set_status("Locating Python…")
        self._log_write("── Checking for compatible Python ──\n")

        python_cmd = self._find_system_python()
        if not python_cmd:
            self.after(0, lambda: self._set_task("python", "error"))
            self._set_status("Could not install Python 3.12.", "#ef5350")
            self.after(0, self._show_error(
                "Could not find or install Python 3.12.\n\n"
                "Please download it manually from:\n"
                "https://www.python.org/downloads/release/python-3128/\n\n"
                "Make sure to check 'Add Python to PATH' during installation,\n"
                "then relaunch BetterTTS."
            ))
            return

        self.after(0, lambda: self._set_task("python", "done"))
        step += 1
        self._set_progress(step / steps)

        # 2. Virtual environment
        self.after(0, lambda: self._set_task("venv", "running"))
        self._set_status("Creating virtual environment…")
        self._log_write("── Creating venv ──\n")

        venv_path = os.path.join(BASE_DIR, "venv")
        if os.path.exists(venv_path):
            self._log_write("venv already exists, reusing.\n")
        else:
            rc, out = run(python_cmd + ["-m", "venv", venv_path])
            self._log_write(out or "(no output)\n")
            if rc != 0:
                self.after(0, lambda: self._set_task("venv", "error"))
                self._set_status("Failed to create venv.", "#ef5350")
                self.after(0, self._show_error("Failed to create virtual environment.\nSee log for details."))
                return

        self.after(0, lambda: self._set_task("venv", "done"))
        step += 1
        self._set_progress(step / steps)

        pip = find_venv_pip()
        python = find_venv_python()
        if not pip or not python:
            self._set_status("Could not find venv pip/python.", "#ef5350")
            return

        # 2. PyTorch
        self.after(0, lambda: self._set_task("torch", "running"))
        gpu_type = self._detected_gpu_type
        gpu_name = self._detected_gpu_name

        if gpu_type == "nvidia":
            if is_blackwell(gpu_name):
                torch_url = "https://download.pytorch.org/whl/cu128"
                self._set_status("Installing PyTorch (CUDA 12.8 — Blackwell)…")
                self._log_write("\n── Installing PyTorch cu128 ──\n")
            else:
                torch_url = "https://download.pytorch.org/whl/cu118"
                self._set_status("Installing PyTorch (CUDA 11.8)…")
                self._log_write("\n── Installing PyTorch cu118 ──\n")

            rc = run_stream(
                [pip, "install", "--no-cache-dir", "--progress-bar", "on",
                 "torch", "torchvision", "torchaudio", "--index-url", torch_url],
                on_line=self._log_write
            )

            if rc != 0:
                self._log_write("\nCUDA install failed, trying CPU fallback…\n")
                rc = run_stream(
                    [pip, "install", "--no-cache-dir", "--progress-bar", "on",
                     "torch", "torchvision", "torchaudio"],
                    on_line=self._log_write
                )
        else:
            self._set_status("Installing PyTorch (CPU)…")
            self._log_write("\n── Installing PyTorch (CPU) ──\n")
            rc = run_stream(
                [pip, "install", "--no-cache-dir", "--progress-bar", "on",
                 "torch", "torchvision", "torchaudio"],
                on_line=self._log_write
            )

        if rc != 0:
            self.after(0, lambda: self._set_task("torch", "error"))
            self._set_status("PyTorch install failed.", "#ef5350")
            return

        self.after(0, lambda: self._set_task("torch", "done"))
        step += 1
        self._set_progress(step / steps)

        # 3. Requirements
        self.after(0, lambda: self._set_task("deps", "running"))
        self._set_status("Installing BetterTTS dependencies…")
        self._log_write("\n── pip install -r requirements.txt ──\n")

        req_path = os.path.join(BASE_DIR, "requirements.txt")
        rc = run_stream(
            [pip, "install", "--no-cache-dir", "--progress-bar", "on", "-r", req_path],
            on_line=self._log_write
        )

        if rc != 0:
            self.after(0, lambda: self._set_task("deps", "error"))
            self._set_status("Dependency install failed.", "#ef5350")
            return

        self.after(0, lambda: self._set_task("deps", "done"))
        step += 1
        self._set_progress(step / steps)

        # 4. Voices directory
        self.after(0, lambda: self._set_task("voices", "running"))
        voices_path = os.path.join(BASE_DIR, "voices")
        os.makedirs(voices_path, exist_ok=True)
        self._log_write("\n── Created voices/ directory ──\n")
        self.after(0, lambda: self._set_task("voices", "done"))
        step += 1
        self._set_progress(step / steps)

        # 5. Save .gpu_type
        self.after(0, lambda: self._set_task("config", "running"))
        gpu_file = os.path.join(BASE_DIR, ".gpu_type")
        with open(gpu_file, "w") as f:
            f.write(gpu_type)
        self._log_write(f"\n── Saved .gpu_type = {gpu_type} ──\n")
        self.after(0, lambda: self._set_task("config", "done"))
        step += 1
        self._set_progress(step / steps)

        # Done
        self.after(0, self._show_step_done)

    # ── Step 4: Done ──────────────────────────────────────────────────────────

    def _show_step_done(self):
        self._log_frame.pack_forget()
        self._progress.pack_forget()
        self._clear_content()
        self._set_step("Complete")

        ctk.CTkLabel(
            self._content,
            text="✓  Setup Complete",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#66bb6a"
        ).pack(anchor="w", pady=(0, 8))

        gpu_colors = {"nvidia": "#66bb6a", "amd": "#ffa726", "intel": "#42a5f5", "cpu": "#aaa"}
        color = gpu_colors.get(self._detected_gpu_type, "#aaa")

        summary = ctk.CTkFrame(self._content, fg_color=("#1a1a2e", "#1a1a2e"), corner_radius=8)
        summary.pack(fill="x", pady=(0, 16))

        for label, value, vc in [
            ("GPU", self._detected_gpu_name, color),
            ("Backend", self._detected_gpu_type.upper(), color),
        ]:
            row = ctk.CTkFrame(summary, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(row, text=f"{label}:", font=ctk.CTkFont(size=12), text_color="#888", width=70, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, font=ctk.CTkFont(size=12, weight="bold"), text_color=vc).pack(side="left")

        notes = {
            "nvidia": "NVIDIA CUDA detected — you'll get the best TTS performance.",
            "amd":    "AMD GPU detected. PyTorch will use CPU on Windows.\nTTS will work, just slower than NVIDIA.",
            "intel":  "Intel GPU detected. PyTorch will use CPU.\nTTS will work, just slower than NVIDIA.",
            "cpu":    "No GPU detected. TTS runs on CPU — it works, but slower.\nAn NVIDIA GPU (RTX 3060+) is recommended for best results.",
        }
        note = notes.get(self._detected_gpu_type, "")
        ctk.CTkLabel(
            summary, text=note,
            font=ctk.CTkFont(size=12),
            text_color="#aaa",
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            self._content,
            text="On first launch, BetterTTS will download the AI model (~2.5–4.5 GB).\nThis is a one-time download.",
            font=ctk.CTkFont(size=12),
            text_color="#888",
            justify="left"
        ).pack(anchor="w", pady=(0, 20))

        btn_row = ctk.CTkFrame(self._content, fg_color="transparent")
        btn_row.pack(anchor="e")

        ctk.CTkButton(
            btn_row,
            text="Launch BetterTTS",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=160, height=38,
            fg_color="#2e7d32", hover_color="#1b5e20",
            command=self._launch_app
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row,
            text="Close",
            font=ctk.CTkFont(size=13),
            width=100, height=38,
            fg_color="transparent",
            border_width=1,
            command=self.destroy
        ).pack(side="right")

    def _launch_app(self):
        python = find_venv_python()
        if python:
            main_path = os.path.join(BASE_DIR, "app", "main.py")
            if not os.path.exists(main_path):
                main_path = os.path.join(BASE_DIR, "main.py")
            NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            subprocess.Popen([python, main_path], cwd=BASE_DIR, creationflags=NO_WINDOW)
        self.destroy()

    def _show_error(self, msg):
        def _inner():
            from tkinter import messagebox
            messagebox.showerror("Setup Error", msg)
        return _inner

    def _on_close(self):
        if self._setup_thread and self._setup_thread.is_alive():
            from tkinter import messagebox
            if messagebox.askyesno("Cancel Setup", "Setup is still running. Are you sure you want to quit?"):
                self.destroy()
        else:
            self.destroy()


# ────────────────────────────────────────────────────────────────────────────────

def should_run_setup():
    """Return True if setup hasn't been completed yet."""
    base = Path(get_base_dir())
    gpu_file = base / ".gpu_type"
    venv_python = (
        base / "venv" / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else base / "venv" / "bin" / "python"
    )
    return not gpu_file.exists() or not venv_python.exists()


if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()