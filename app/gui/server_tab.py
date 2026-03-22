import customtkinter as ctk

from app.constants import DEFAULT_PORT
from app.model_manager import ModelState
import app.gui.theme as theme
from app.gui.theme import C, F, BTN_SUCCESS, BTN_DANGER, BTN_SECONDARY, card
from app.gui.widgets import StatusIndicator, SectionHeader, InfoLabel, CardFrame


class ServerTab:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(
            self.parent, fg_color="transparent",
            scrollbar_button_color=C.BG_INPUT,
            scrollbar_button_hover_color=C.ACCENT,
        )
        scroll.pack(fill="both", expand=True)
        p = scroll

        # ── Server status card ──────────────────────────────
        status_card = CardFrame(p)
        status_card.pack(fill="x", padx=16, pady=(16, 0))

        SectionHeader(status_card, text="TTS Server").pack(
            anchor="w", padx=16, pady=(14, 4))

        InfoLabel(status_card, text=(
            "The server listens for TTS requests from Streamer.bot (or any HTTP client). "
            "Load a model first, then start the server."
        )).pack(anchor="w", padx=16, pady=(0, 10))

        # Status row
        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(0, 6))

        self.indicator = StatusIndicator(status_row, color="gray")
        self.indicator.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(
            status_row, text="Server stopped",
            font=F.BODY, text_color=C.TEXT_SEC, anchor="w",
        )
        self.status_label.pack(side="left")

        # Port + buttons row
        ctrl_row = ctk.CTkFrame(status_card, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=16, pady=(4, 14))

        ctk.CTkLabel(ctrl_row, text="Port:", font=F.BODY, text_color=C.TEXT_SEC).pack(side="left")
        self.port_entry = ctk.CTkEntry(
            ctrl_row, width=80, font=F.BODY, height=34,
            fg_color=C.BG_INPUT, border_color=C.BORDER, corner_radius=8,
        )
        self.port_entry.insert(0, str(self.app.config_data.get("port", DEFAULT_PORT)))
        self.port_entry.pack(side="left", padx=(8, 16))

        self.start_btn = ctk.CTkButton(
            ctrl_row, text="Start Server", command=self._start_clicked,
            width=140, height=36, **BTN_SUCCESS,
            font=("Segoe UI", 13, "bold"),
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            ctrl_row, text="Stop Server", command=self._stop_clicked,
            width=120, height=36, state="disabled", **BTN_DANGER,
        )
        self.stop_btn.pack(side="left")

        # ── Endpoint URL card ───────────────────────────────
        url_card = CardFrame(p)
        url_card.pack(fill="x", padx=16, pady=(10, 0))

        ctk.CTkLabel(
            url_card, text="Endpoint URL", font=F.HEADING,
            text_color=C.TEXT,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        url_row = ctk.CTkFrame(url_card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(0, 12))

        port = self.app.config_data.get("port", DEFAULT_PORT)
        self.url_label = ctk.CTkLabel(
            url_row, text=f"http://localhost:{port}/tts",
            font=F.MONO, text_color=C.LINK,
        )
        self.url_label.pack(side="left")

        self.copy_btn = ctk.CTkButton(
            url_row, text="Copy", width=60, height=28,
            command=self._copy_url, **BTN_SECONDARY,
            font=F.CAPTION,
        )
        self.copy_btn.pack(side="left", padx=(12, 0))

        # ── Setup guide ────────────────────────────────────
        guide_row = ctk.CTkFrame(p, fg_color="transparent")
        guide_row.pack(fill="x", padx=16, pady=(16, 16))

        ctk.CTkButton(
            guide_row, text="Open Setup Guide",
            command=self._open_guide, width=200, height=36,
            **BTN_SECONDARY, font=("Segoe UI", 13),
        ).pack(side="left")

        InfoLabel(guide_row, text=(
            "  Step-by-step instructions for connecting to Streamer.bot"
        ), wraplength=int(400 * theme.UI_SCALE)).pack(side="left", padx=(12, 0))

    # ── Actions ─────────────────────────────────────────────

    def _get_port(self) -> int:
        try:
            return int(self.port_entry.get().strip())
        except ValueError:
            return DEFAULT_PORT

    def _start_clicked(self):
        if self.app.model_manager.state != ModelState.READY:
            self.status_label.configure(
                text="Load a model first (Model tab)", text_color=C.ERROR,
            )
            self.indicator.set_color("red")
            return

        port = self._get_port()
        self.app.config_data["port"] = port
        self.app.save()
        self.app.server_manager.set_port(port)

        try:
            self.app.server_manager.start()
            self.indicator.set_color("green")
            self.status_label.configure(
                text=f"Server running on port {port}", text_color=C.SUCCESS,
            )
            self.url_label.configure(text=f"http://localhost:{port}/tts")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.port_entry.configure(state="disabled")
        except Exception as e:
            self.indicator.set_color("red")
            self.status_label.configure(
                text=f"Failed to start: {e}", text_color=C.ERROR,
            )

    def _stop_clicked(self):
        self.app.server_manager.stop()
        self.indicator.set_color("gray")
        self.status_label.configure(text="Server stopped", text_color=C.TEXT_SEC)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.port_entry.configure(state="normal")

    def _copy_url(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.url_label.cget("text"))
        self.copy_btn.configure(text="Copied!")
        self.parent.after(1500, lambda: self.copy_btn.configure(text="Copy"))

    def _open_guide(self):
        from app.gui.setup_wizard import SetupWizard
        SetupWizard(self.app, self.app.config_data, on_close=self.app.save)

    def update_model_state(self, state: ModelState):
        if state != ModelState.READY and self.app.server_manager.is_running:
            self._stop_clicked()
