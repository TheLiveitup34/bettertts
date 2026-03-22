import threading
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog

from app.constants import ModelVariant
from app.model_manager import ModelState
from app.gui.theme import C, F, BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER
from app.gui.widgets import SectionHeader, InfoLabel, CardFrame


class ProfilesTab:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.parent = parent
        self._build()
        self._refresh_list()

    def _build(self):
        # Scrollable container so content doesn't get clipped
        scroll = ctk.CTkScrollableFrame(
            self.parent, fg_color="transparent",
            scrollbar_button_color=C.BG_INPUT,
            scrollbar_button_hover_color=C.ACCENT,
        )
        scroll.pack(fill="both", expand=True)
        p = scroll

        # ── Info + active profile card ──────────────────────
        info_card = CardFrame(p)
        info_card.pack(fill="x", padx=16, pady=(16, 0))

        SectionHeader(info_card, text="Voice Profiles").pack(
            anchor="w", padx=16, pady=(14, 4))

        InfoLabel(info_card, text=(
            "Create voice profiles by uploading a short audio clip (5-15 seconds) of the "
            "voice you want to clone, along with an exact transcript of what is said. "
            "Requires a Base model (see Model tab)."
        )).pack(anchor="w", padx=16, pady=(0, 8))

        self.active_label = ctk.CTkLabel(
            info_card, text="Active Profile: None",
            font=("Segoe UI", 13, "bold"), text_color=C.ACCENT_LIGHT,
            anchor="w",
        )
        self.active_label.pack(padx=16, pady=(0, 12), anchor="w")

        # ── Create new profile card ─────────────────────────
        create_card = CardFrame(p)
        create_card.pack(fill="x", padx=16, pady=(10, 0))

        SectionHeader(create_card, text="Create New Profile").pack(
            anchor="w", padx=16, pady=(14, 8))

        # Name
        name_row = ctk.CTkFrame(create_card, fg_color="transparent")
        name_row.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(name_row, text="Name", font=F.BODY_SM, text_color=C.TEXT_SEC, width=80).pack(side="left")
        self.name_entry = ctk.CTkEntry(
            name_row, placeholder_text='e.g. "Morgan Freeman"',
            font=F.BODY_SM, height=32,
            fg_color=C.BG_INPUT, border_color=C.BORDER, corner_radius=8,
        )
        self.name_entry.pack(side="left", fill="x", expand=True)

        # Audio file
        audio_row = ctk.CTkFrame(create_card, fg_color="transparent")
        audio_row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(audio_row, text="Audio", font=F.BODY_SM, text_color=C.TEXT_SEC, width=80).pack(side="left")
        self.audio_entry = ctk.CTkEntry(
            audio_row, placeholder_text="Select a .wav, .mp3, or .flac file...",
            font=F.BODY_SM, height=32,
            fg_color=C.BG_INPUT, border_color=C.BORDER, corner_radius=8,
        )
        self.audio_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            audio_row, text="Browse", width=70, height=30,
            command=self._browse_audio, **BTN_SECONDARY,
            font=F.CAPTION,
        ).pack(side="left")

        # Transcript
        trans_row = ctk.CTkFrame(create_card, fg_color="transparent")
        trans_row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(trans_row, text="Transcript", font=F.BODY_SM, text_color=C.TEXT_SEC, width=80).pack(side="left", anchor="n")
        self.transcript_text = ctk.CTkTextbox(
            trans_row, height=50, font=F.BODY_SM,
            fg_color=C.BG_INPUT, text_color=C.TEXT, corner_radius=8,
        )
        self.transcript_text.pack(side="left", fill="x", expand=True)

        InfoLabel(create_card, text=(
            "Type exactly what is said in the audio clip. This helps the AI learn the voice."
        )).pack(padx=16, pady=(2, 6), anchor="w")

        # Save button
        btn_row = ctk.CTkFrame(create_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        self.save_btn = ctk.CTkButton(
            btn_row, text="Save Profile", command=self._save_profile,
            width=130, height=34, font=("Segoe UI", 13, "bold"),
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            text_color="#ffffff", corner_radius=8,
        )
        self.save_btn.pack(side="left")

        self.save_status = ctk.CTkLabel(
            btn_row, text="", font=F.CAPTION, text_color=C.TEXT_DIM,
        )
        self.save_status.pack(side="left", padx=(12, 0))

        # ── Saved profiles list ─────────────────────────────
        list_card = CardFrame(p)
        list_card.pack(fill="x", padx=16, pady=(10, 16))

        SectionHeader(list_card, text="Saved Profiles").pack(
            anchor="w", padx=16, pady=(14, 8))

        self.list_frame = ctk.CTkScrollableFrame(
            list_card, height=130,
            fg_color=C.BG_CARD, corner_radius=0,
        )
        self.list_frame.pack(fill="x", padx=8, pady=(0, 12))

        # Overlay for when wrong model is loaded
        self.overlay_label = ctk.CTkLabel(
            p, text="", font=F.BODY_SM, text_color=C.WARNING,
        )

    def _browse_audio(self):
        path = filedialog.askopenfilename(
            title="Select Reference Audio",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.m4a"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.audio_entry.delete(0, "end")
            self.audio_entry.insert(0, path)

    def _save_profile(self):
        name = self.name_entry.get().strip()
        audio_path = self.audio_entry.get().strip()
        transcript = self.transcript_text.get("1.0", "end").strip()

        if not name:
            self.save_status.configure(text="Enter a profile name", text_color=C.ERROR)
            return
        if not audio_path:
            self.save_status.configure(text="Select an audio file", text_color=C.ERROR)
            return
        if not transcript:
            self.save_status.configure(text="Enter the transcript of the audio", text_color=C.ERROR)
            return

        try:
            self.app.profile_manager.create_profile(name, audio_path, transcript)
            self.save_status.configure(text=f"Saved '{name}'!", text_color=C.SUCCESS)
            self.name_entry.delete(0, "end")
            self.audio_entry.delete(0, "end")
            self.transcript_text.delete("1.0", "end")
            self._refresh_list()
        except Exception as e:
            self.save_status.configure(text=str(e)[:100], text_color=C.ERROR)

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        profiles = self.app.profile_manager.profiles
        active_name = self.app.profile_manager.active_name

        self.active_label.configure(
            text=f"Active Profile: {active_name}" if active_name else "Active Profile: None"
        )

        if not profiles:
            ctk.CTkLabel(
                self.list_frame, text="No voice profiles yet. Create one above.",
                font=F.BODY_SM, text_color=C.TEXT_DIM,
            ).pack(pady=10)
            return

        for profile in profiles:
            row = ctk.CTkFrame(self.list_frame, fg_color=C.BG_INPUT, corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)

            is_active = profile.name == active_name
            name_color = C.SUCCESS if is_active else C.TEXT

            ctk.CTkLabel(
                row, text=profile.name,
                font=("Segoe UI", 12, "bold" if is_active else "normal"),
                text_color=name_color, anchor="w", width=180,
            ).pack(side="left", padx=(10, 0))

            ctk.CTkLabel(
                row, text=f"({profile.audio_file})",
                font=F.CAPTION, text_color=C.TEXT_DIM, anchor="w",
            ).pack(side="left", padx=(4, 0))

            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right", padx=6, pady=4)

            if not is_active:
                ctk.CTkButton(
                    btn_frame, text="Set Active", width=80, height=26,
                    font=F.CAPTION, **BTN_PRIMARY,
                    command=lambda n=profile.name: self._set_active(n),
                ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_frame, text="Test", width=50, height=26,
                font=F.CAPTION, **BTN_SECONDARY,
                command=lambda n=profile.name: self._test_profile(n),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_frame, text="Delete", width=60, height=26,
                font=F.CAPTION, **BTN_DANGER,
                command=lambda n=profile.name: self._delete_profile(n),
            ).pack(side="left", padx=2)

    def _set_active(self, name: str):
        self.app.profile_manager.set_active(name)
        self._refresh_list()

    def _delete_profile(self, name: str):
        self.app.profile_manager.delete_profile(name)
        self._refresh_list()

    def _test_profile(self, name: str):
        if self.app.model_manager.state != ModelState.READY:
            self.save_status.configure(text="Load a Base model first", text_color=C.ERROR)
            return

        profile = self.app.profile_manager.get_profile(name)
        if not profile:
            return

        thread = threading.Thread(target=self._run_test, args=(profile,), daemon=True)
        thread.start()

    def _run_test(self, profile):
        try:
            ref_audio = self.app.profile_manager.get_audio_path(profile)
            wav, sr = self.app.model_manager.generate(
                text="Hello, this is a test of the cloned voice profile.",
                speaker="Ryan",
                language="English",
                ref_audio=ref_audio,
                ref_text=profile.transcript,
            )
            import sounddevice as sd
            sd.play(wav, sr)
            sd.wait()
        except Exception as e:
            self.parent.after(0, lambda: self.save_status.configure(
                text=f"Test error: {str(e)[:100]}", text_color=C.ERROR,
            ))

    def update_for_model(self, variant: Optional[ModelVariant]):
        if variant and variant.supports_cloning:
            self.overlay_label.pack_forget()
        else:
            self.overlay_label.configure(
                text="Voice profiles require a Base model for voice cloning. "
                     "Switch to a Base model in the Model tab to use this feature."
            )
            self.overlay_label.pack(anchor="w", padx=16, pady=5)
