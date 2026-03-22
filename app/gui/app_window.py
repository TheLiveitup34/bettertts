import webbrowser
import customtkinter as ctk

from app.config import load_config, save_config
from app.gpu_detect import get_gpu_info
from app.model_manager import ModelManager, ModelState
from app.voice_profiles import VoiceProfileManager
from app.server import ServerManager
import app.gui.theme as theme
from app.gui.theme import C, F, apply_window_theme, card
from app.gui.server_tab import ServerTab
from app.gui.model_tab import ModelTab
from app.gui.voice_tab import VoiceTab
from app.gui.profiles_tab import ProfilesTab


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BetterTTS")
        apply_window_theme(self)  # sets geometry, scaling, and colors

        self.config_data = load_config()
        self.gpu_info = get_gpu_info()

        # Core services
        self.model_manager = ModelManager(on_state_change=self._on_model_state_change)
        self.profile_manager = VoiceProfileManager()
        self.server_manager = ServerManager(
            self.model_manager, self.profile_manager,
            config_data=self.config_data,
            port=self.config_data["port"],
        )

        self._build_header()
        self._build_gpu_bar()

        # Tabs
        self.tabview = ctk.CTkTabview(
            self, anchor="nw",
            fg_color=C.BG_DARK,
            segmented_button_fg_color=C.BG_CARD,
            segmented_button_selected_color=C.ACCENT,
            segmented_button_selected_hover_color=C.ACCENT_HOVER,
            segmented_button_unselected_color=C.BG_CARD,
            segmented_button_unselected_hover_color=C.BG_HOVER,
            corner_radius=10,
        )
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        for name in ("Server", "Model", "Voice", "Profiles"):
            tab = self.tabview.add(name)
            tab.configure(fg_color=C.BG_DARK)

        self.server_tab = ServerTab(self.tabview.tab("Server"), self)
        self.model_tab = ModelTab(self.tabview.tab("Model"), self)
        self.voice_tab = VoiceTab(self.tabview.tab("Voice"), self)
        self.profiles_tab = ProfilesTab(self.tabview.tab("Profiles"), self)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show setup guide on first launch
        if self.config_data.get("show_setup_guide", True):
            self.after(300, self._show_setup_wizard)

    def _build_header(self):
        """Branded title bar."""
        header = ctk.CTkFrame(self, fg_color=C.BG_DARK, height=48)
        header.pack(fill="x", padx=14, pady=(14, 0))
        header.pack_propagate(False)

        # "Better" in accent, "TTS" in white
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(
            title_frame, text="Better", font=F.TITLE,
            text_color=C.ACCENT_LIGHT,
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame, text="TTS", font=F.TITLE,
            text_color=C.TEXT,
        ).pack(side="left")

        ctk.CTkLabel(
            header, text="Qwen3-TTS for Streamers",
            font=F.BODY_SM, text_color=C.TEXT_DIM,
        ).pack(side="left", padx=(12, 0))

        # Credits & donation links (right side)
        links_frame = ctk.CTkFrame(header, fg_color="transparent")
        links_frame.pack(side="right")

        donate_btn = ctk.CTkButton(
            links_frame, text="Consider Donating to help out!", width=210, height=26,
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            text_color="#ffffff", corner_radius=6,
            font=F.CAPTION,
            command=lambda: webbrowser.open("https://streamelements.com/kindredspiritva/tip"),
        )
        donate_btn.pack(side="left", padx=(0, 8))

        credit_btn = ctk.CTkButton(
            links_frame, text="by @kindredspiritva", width=130, height=26,
            fg_color="transparent", hover_color=C.BG_HOVER,
            text_color=C.LINK, corner_radius=6,
            font=("Segoe UI", 11),
            command=lambda: webbrowser.open("https://twitter.com/kindredspirityt"),
        )
        credit_btn.pack(side="left")

    def _build_gpu_bar(self):
        gpu_card = card(self)
        gpu_card.pack(fill="x", padx=14, pady=(8, 6))

        backend = self.gpu_info.get("backend", "CPU")
        gpu_name = self.gpu_info.get("name", "Unknown")

        if self.gpu_info["available"]:
            vram_str = f"VRAM: {self.gpu_info['vram_gb']} GB  |  " if self.gpu_info["vram_gb"] > 0 else ""
            text = (
                f"GPU: {gpu_name}  |  "
                f"{vram_str}"
                f"Backend: {backend} {self.gpu_info.get('backend_version', '')}"
            )
            ctk.CTkLabel(
                gpu_card, text=text, text_color=C.SUCCESS,
                font=F.BODY_SM,
            ).pack(pady=8, padx=14)
        else:
            is_amd = any(kw in gpu_name.lower() for kw in ["radeon", "amd", "ati"])
            is_intel = "intel" in gpu_name.lower() and "nvidia" not in gpu_name.lower()

            if is_amd:
                line1 = f"GPU: {gpu_name}  |  Running on CPU (no GPU acceleration)"
                line2 = (
                    "AMD GPUs are not supported by Qwen3-TTS — it requires NVIDIA CUDA. "
                    "TTS will still work using your CPU, but generation will be slower."
                )
                color = C.WARNING
            elif is_intel:
                line1 = f"GPU: {gpu_name}  |  Running on CPU (no GPU acceleration)"
                line2 = (
                    "Intel GPUs are not supported by Qwen3-TTS — it requires NVIDIA CUDA. "
                    "TTS will still work using your CPU, but generation will be slower."
                )
                color = C.WARNING
            else:
                line1 = "No GPU detected  |  Running on CPU"
                line2 = (
                    "No dedicated GPU was found. TTS will run on your CPU which is slower. "
                    "For best performance, an NVIDIA GPU (GTX 1060+) is recommended."
                )
                color = C.ERROR

            ctk.CTkLabel(
                gpu_card, text=line1, text_color=color,
                font=("Segoe UI", 12, "bold"),
            ).pack(pady=(8, 0), padx=14)
            ctk.CTkLabel(
                gpu_card, text=line2, text_color=C.TEXT_SEC,
                font=F.CAPTION, wraplength=theme.WRAP_WIDE, justify="center",
            ).pack(pady=(2, 8), padx=14)

    def _show_setup_wizard(self):
        from app.gui.setup_wizard import SetupWizard
        SetupWizard(self, self.config_data, on_close=self.save)

    def _on_model_state_change(self, state: ModelState, error: str):
        self.after(0, lambda: self.model_tab.update_state(state, error))
        self.after(0, lambda: self.server_tab.update_model_state(state))
        self.after(0, lambda: self.voice_tab.update_for_model(self.model_manager.current_variant))
        self.after(0, lambda: self.profiles_tab.update_for_model(self.model_manager.current_variant))

    def save(self):
        save_config(self.config_data)

    def _on_close(self):
        self.server_manager.stop()
        self.model_manager.unload_model()
        self.save()
        self.destroy()
