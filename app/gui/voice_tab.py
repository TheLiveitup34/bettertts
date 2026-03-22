import threading
from typing import Optional

import customtkinter as ctk

from app.constants import SPEAKERS, SPEAKER_INFO, LANGUAGES, ModelVariant
from app.model_manager import ModelState
from app.gui.theme import C, F, BTN_PRIMARY, BTN_SECONDARY
from app.gui.widgets import SectionHeader, InfoLabel, CardFrame


class VoiceTab:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.parent = parent
        self._build()

    def _build(self):
        # Scrollable container so content doesn't get clipped
        scroll = ctk.CTkScrollableFrame(
            self.parent, fg_color="transparent",
            scrollbar_button_color=C.BG_INPUT,
            scrollbar_button_hover_color=C.ACCENT,
        )
        scroll.pack(fill="both", expand=True)
        p = scroll

        # ── Voice settings card ─────────────────────────────
        voice_card = CardFrame(p)
        voice_card.pack(fill="x", padx=16, pady=(16, 0))

        SectionHeader(voice_card, text="Voice Settings").pack(
            anchor="w", padx=16, pady=(14, 8))

        # --- Speaker section (only for CustomVoice models) ---
        self.speaker_frame = ctk.CTkFrame(voice_card, fg_color="transparent")
        self.speaker_frame.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            self.speaker_frame, text="Speaker", font=F.BODY,
            text_color=C.TEXT_SEC,
        ).pack(anchor="w")

        speaker_row = ctk.CTkFrame(self.speaker_frame, fg_color="transparent")
        speaker_row.pack(fill="x")

        self.speaker_var = ctk.StringVar(value=self.app.config_data.get("speaker", "Ryan"))
        self.speaker_menu = ctk.CTkOptionMenu(
            speaker_row, variable=self.speaker_var, values=SPEAKERS,
            command=self._on_speaker_change, width=200, height=32,
            fg_color=C.BG_INPUT, button_color=C.ACCENT,
            button_hover_color=C.ACCENT_HOVER,
            dropdown_fg_color=C.BG_CARD, dropdown_hover_color=C.BG_HOVER,
            corner_radius=8, font=F.BODY,
        )
        self.speaker_menu.pack(side="left", pady=3)

        self.speaker_info = ctk.CTkLabel(
            speaker_row, text=SPEAKER_INFO.get(self.speaker_var.get(), ""),
            font=F.CAPTION, text_color=C.TEXT_DIM,
        )
        self.speaker_info.pack(side="left", padx=(12, 0))

        # --- Language ---
        lang_frame = ctk.CTkFrame(voice_card, fg_color="transparent")
        lang_frame.pack(fill="x", padx=16, pady=(6, 6))

        ctk.CTkLabel(lang_frame, text="Language", font=F.BODY, text_color=C.TEXT_SEC).pack(anchor="w")
        self.lang_var = ctk.StringVar(value=self.app.config_data.get("language", "English"))
        self.lang_menu = ctk.CTkOptionMenu(
            lang_frame, variable=self.lang_var, values=LANGUAGES,
            command=self._on_lang_change, width=200, height=32,
            fg_color=C.BG_INPUT, button_color=C.ACCENT,
            button_hover_color=C.ACCENT_HOVER,
            dropdown_fg_color=C.BG_CARD, dropdown_hover_color=C.BG_HOVER,
            corner_radius=8, font=F.BODY,
        )
        self.lang_menu.pack(anchor="w", pady=3)

        # --- Instruct / tone ---
        self.instruct_frame = ctk.CTkFrame(voice_card, fg_color="transparent")
        self.instruct_frame.pack(fill="x", padx=16, pady=(6, 0))

        self.instruct_label = ctk.CTkLabel(
            self.instruct_frame, text="Style Instruction (optional)",
            font=F.BODY, text_color=C.TEXT_SEC,
        )
        self.instruct_label.pack(anchor="w")

        self.instruct_help = InfoLabel(self.instruct_frame, text=(
            "Tell the AI how to speak. Examples: 'Speak cheerfully and energetically', "
            "'Use a calm, soothing tone', 'Read this like a news anchor', "
            "'Whisper dramatically'"
        ))
        self.instruct_help.pack(anchor="w", pady=(0, 4))

        self.instruct_text = ctk.CTkTextbox(
            self.instruct_frame, height=60, font=F.BODY_SM,
            fg_color=C.BG_INPUT, text_color=C.TEXT,
            corner_radius=8,
        )
        self.instruct_text.pack(fill="x", pady=3)
        if self.app.config_data.get("instruct"):
            self.instruct_text.insert("1.0", self.app.config_data["instruct"])

        save_row = ctk.CTkFrame(self.instruct_frame, fg_color="transparent")
        save_row.pack(fill="x", pady=(4, 14))

        self.save_instruct_btn = ctk.CTkButton(
            save_row, text="Save", command=self._save_instruct_clicked,
            width=80, height=30, **BTN_PRIMARY,
        )
        self.save_instruct_btn.pack(side="left")

        self.save_instruct_status = ctk.CTkLabel(
            save_row, text="", font=F.CAPTION, text_color=C.TEXT_DIM,
        )
        self.save_instruct_status.pack(side="left", padx=(10, 0))

        # ── Test TTS card ───────────────────────────────────
        test_card = CardFrame(p)
        test_card.pack(fill="x", padx=16, pady=(10, 16))

        SectionHeader(test_card, text="Test TTS").pack(
            anchor="w", padx=16, pady=(14, 8))

        test_frame = ctk.CTkFrame(test_card, fg_color="transparent")
        test_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.test_entry = ctk.CTkEntry(
            test_frame, placeholder_text="Type text to test...",
            font=F.BODY_SM, height=36,
            fg_color=C.BG_INPUT, border_color=C.BORDER, corner_radius=8,
        )
        self.test_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.test_entry.insert(0, "Hello, welcome to the stream!")

        self.test_btn = ctk.CTkButton(
            test_frame, text="Test", command=self._test_clicked,
            width=80, height=36, **BTN_PRIMARY,
            font=("Segoe UI", 13, "bold"),
        )
        self.test_btn.pack(side="left")

        self.test_status = ctk.CTkLabel(
            test_card, text="", font=F.CAPTION, text_color=C.TEXT_DIM,
        )
        self.test_status.pack(anchor="w", padx=16, pady=(0, 12))

    # ── Callbacks ───────────────────────────────────────────

    def _on_speaker_change(self, _=None):
        speaker = self.speaker_var.get()
        self.speaker_info.configure(text=SPEAKER_INFO.get(speaker, ""))
        self.app.config_data["speaker"] = speaker
        self.app.save()

    def _on_lang_change(self, _=None):
        self.app.config_data["language"] = self.lang_var.get()
        self.app.save()

    def _get_instruct(self) -> str:
        return self.instruct_text.get("1.0", "end").strip()

    def _save_instruct_clicked(self):
        self.app.config_data["instruct"] = self._get_instruct()
        self.app.save()
        self.save_instruct_status.configure(text="Saved!", text_color=C.SUCCESS)
        self.parent.after(2000, lambda: self.save_instruct_status.configure(text=""))

    def _save_instruct(self):
        self.app.config_data["instruct"] = self._get_instruct()
        self.app.save()

    def _test_clicked(self):
        if self.app.model_manager.state != ModelState.READY:
            self.test_status.configure(
                text="Load a model first (Model tab)", text_color=C.ERROR,
            )
            return

        text = self.test_entry.get().strip()
        if not text:
            self.test_status.configure(text="Enter some text first", text_color=C.WARNING)
            return

        self._save_instruct()
        self.test_btn.configure(state="disabled", text="...")
        self.test_status.configure(text="Generating audio...", text_color=C.WARNING)

        thread = threading.Thread(target=self._run_test, args=(text,), daemon=True)
        thread.start()

    def _run_test(self, text: str):
        try:
            ref_audio = ""
            ref_text = ""
            variant = self.app.model_manager.current_variant
            if variant and variant.supports_cloning:
                active = self.app.profile_manager.active_profile
                if active:
                    ref_audio = self.app.profile_manager.get_audio_path(active)
                    ref_text = active.transcript

            wav, sr = self.app.model_manager.generate(
                text=text,
                speaker=self.speaker_var.get(),
                language=self.lang_var.get(),
                instruct=self._get_instruct(),
                ref_audio=ref_audio,
                ref_text=ref_text,
            )
            import sounddevice as sd
            sd.play(wav, sr)
            self.parent.after(0, lambda: self.test_status.configure(
                text="Playing audio...", text_color=C.SUCCESS,
            ))
            sd.wait()
            self.parent.after(0, lambda: self.test_status.configure(
                text="Done!", text_color=C.SUCCESS,
            ))
        except Exception as e:
            self.parent.after(0, lambda: self.test_status.configure(
                text=f"Error: {str(e)[:150]}", text_color=C.ERROR,
            ))
        finally:
            self.parent.after(0, lambda: self.test_btn.configure(state="normal", text="Test"))

    def update_for_model(self, variant: Optional[ModelVariant]):
        """Adapt visible controls based on the loaded model variant type."""
        if variant is None:
            return

        if variant.supports_speakers:
            self.speaker_frame.pack(fill="x", padx=16, pady=(0, 6))
            self.instruct_label.configure(text="Style Instruction (optional)")
            self.instruct_help.configure(text=(
                "Tell the AI how to speak. Examples: 'Speak cheerfully and energetically', "
                "'Use a calm, soothing tone', 'Read this like a news anchor'"
            ))
        elif variant.supports_voice_design:
            self.speaker_frame.pack_forget()
            self.instruct_label.configure(text="Voice Description (required)")
            self.instruct_help.configure(text=(
                "Describe the voice you want the AI to create. Example: "
                "'A warm female voice with a slight British accent, speaking calmly and clearly'"
            ))
        elif variant.supports_cloning:
            self.speaker_frame.pack_forget()
            self.instruct_label.configure(text="Style Instruction")
            self.instruct_help.configure(text=(
                "Voice cloning uses the active voice profile from the Profiles tab. "
                "The instruct field is not used for voice cloning."
            ))
