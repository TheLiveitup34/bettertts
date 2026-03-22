import customtkinter as ctk
import app.gui.theme as theme
from app.gui.theme import C, F, BTN_PRIMARY, BTN_SECONDARY, BTN_GHOST


STEPS = [
    {
        "title": "Welcome to BetterTTS!",
        "body": (
            "This guide will walk you through getting BetterTTS\n"
            "up and running with Streamer.bot.\n\n"
            "It only takes a few minutes. Let's get started!"
        ),
    },
    {
        "title": "Step 1 — Load a Model",
        "body": (
            'Go to the "Model" tab and pick a model size:\n\n'
            '  \u2022 CustomVoice 0.6B  \u2014  Fast, low VRAM (~4 GB). Best for most streamers.\n'
            '  \u2022 CustomVoice 1.7B  \u2014  Higher quality, needs ~6-8 GB VRAM.\n'
            '  \u2022 Base models       \u2014  Clone any voice from an audio clip.\n'
            '  \u2022 VoiceDesign       \u2014  Describe a voice in words and the AI creates it.\n\n'
            'Click "Load Model". The first time, the model will be downloaded\n'
            'automatically (1\u20145 GB depending on size). This only happens once.\n\n'
            'Wait until the status turns green and says "Model loaded".'
        ),
    },
    {
        "title": "Step 2 — Start the Server",
        "body": (
            'Go to the "Server" tab and click "Start Server".\n\n'
            "The status should turn green and show:\n"
            '  "Server running on port 7861"\n\n'
            "BetterTTS is now listening for TTS requests.\n"
            "The port can be changed if needed, but 7861 is the default\n"
            "and matches the Streamer.bot code."
        ),
    },
    {
        "title": "Step 3 — Import into Streamer.bot",
        "body": (
            "In the BetterTTS folder you'll find a file:\n"
            '  "BetterTTS_Streamerbot_Import.txt"\n\n'
            "To import it into Streamer.bot:\n\n"
            "  1. Open Streamer.bot\n"
            '  2. Click the "Import" button at the top menu bar\n'
            "  3. Open the import file, copy the entire string,\n"
            "     and paste it into the Import String box\n"
            '  4. Click "Import" at the bottom\n\n'
            'This will create "Set Global Variable for ttsText" and a C# code\n'
            "block to play the TTS, add these to whatever actions you want the\n"
            "TTS to trigger as well as the respective text in the global variable."
        ),
    },
    {
        "title": "Step 4 — Enable Queue Pausing",
        "body": (
            "IMPORTANT: Make sure the BetterTTS queue won't let\n"
            "TTS messages overlap each other.\n\n"
            "  1. In Streamer.bot, go to the Action Queues tab\n"
            '  2. Find the "BetterTTS" queue\n'
            '  3. Make sure "Blocking" is enabled (checked)\n\n'
            "When Blocking is on, each TTS request must finish\n"
            "playing before the next one starts. Without this,\n"
            "multiple TTS messages could play at the same time\n"
            "and overlap each other.\n\n"
            "If you don't see the BetterTTS queue, right-click\n"
            'in the Action Queues panel and create one named "BetterTTS"\n'
            "with Blocking enabled, then assign your action to it."
        ),
    },
    {
        "title": "Step 5 — Test It!",
        "body": (
            "Make sure:\n"
            "  \u2714  BetterTTS is running with a model loaded\n"
            "  \u2714  The server is started (green status)\n"
            "  \u2714  Streamer.bot is running with the imported action\n"
            "  \u2714  BetterTTS queue has Blocking enabled\n\n"
            'Type  !tts Hello world  in your Twitch chat.\n\n'
            "You should hear the AI voice read the message!\n\n"
            "Each message queues up and plays one at a time.\n"
            "The code blocks until playback finishes, then clears\n"
            "ttsText automatically so it doesn't repeat.\n\n"
            "Tip: You can customize the speaker, language, and voice\n"
            'instructions in the "Voice" tab or directly in the C# code.'
        ),
    },
]


class SetupWizard(ctk.CTkToplevel):
    """A step-by-step setup guide shown as a modal popup."""

    def __init__(self, master, config_data: dict, on_close=None):
        super().__init__(master)
        self.title("BetterTTS \u2014 Setup Guide")
        wiz_w = int(580 * theme.UI_SCALE)
        wiz_h = int(470 * theme.UI_SCALE)
        self.geometry(f"{wiz_w}x{wiz_h}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=C.BG_DARK)

        self._config = config_data
        self._on_close = on_close
        self._current_step = 0

        # Title
        self._title_label = ctk.CTkLabel(
            self, text="", font=F.HEADING_LG, text_color=C.ACCENT_LIGHT,
            anchor="w",
        )
        self._title_label.pack(fill="x", padx=28, pady=(24, 6))

        # Separator
        ctk.CTkFrame(self, height=1, fg_color=C.SEPARATOR).pack(
            fill="x", padx=28, pady=(0, 12))

        # Body
        self._body_label = ctk.CTkLabel(
            self, text="", font=F.BODY, text_color=C.TEXT_SEC,
            justify="left", anchor="nw", wraplength=int(520 * theme.UI_SCALE),
        )
        self._body_label.pack(fill="both", expand=True, padx=28, pady=(4, 10))

        # Step dots
        self._dots_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._dots_frame.pack(pady=(0, 8))

        self._dots = []
        for i in range(len(STEPS)):
            dot = ctk.CTkFrame(
                self._dots_frame, width=8, height=8,
                corner_radius=4, fg_color=C.TEXT_DIM,
            )
            dot.pack(side="left", padx=3)
            self._dots.append(dot)

        # Bottom bar
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=28, pady=(0, 18))

        # Don't show again checkbox
        self._dont_show_var = ctk.BooleanVar(
            value=not config_data.get("show_setup_guide", True)
        )
        self._checkbox = ctk.CTkCheckBox(
            bottom, text="Don't show at launch",
            variable=self._dont_show_var,
            font=F.BODY_SM, text_color=C.TEXT_DIM,
            fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
            command=self._on_checkbox_toggle,
        )
        self._checkbox.pack(side="left")

        # Buttons (right side)
        self._close_btn = ctk.CTkButton(
            bottom, text="Close", width=80, height=34,
            command=self._close, **BTN_GHOST,
        )
        self._close_btn.pack(side="right", padx=(8, 0))

        self._next_btn = ctk.CTkButton(
            bottom, text="Next", width=100, height=34,
            command=self._next_step, **BTN_PRIMARY,
            font=("Segoe UI", 13, "bold"),
        )
        self._next_btn.pack(side="right", padx=(8, 0))

        self._back_btn = ctk.CTkButton(
            bottom, text="Back", width=80, height=34,
            command=self._prev_step, **BTN_GHOST,
        )
        self._back_btn.pack(side="right")

        self._show_step()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _show_step(self):
        step = STEPS[self._current_step]
        self._title_label.configure(text=step["title"])
        self._body_label.configure(text=step["body"])

        # Update dots
        for i, dot in enumerate(self._dots):
            if i == self._current_step:
                dot.configure(fg_color=C.ACCENT)
            elif i < self._current_step:
                dot.configure(fg_color=C.SUCCESS)
            else:
                dot.configure(fg_color=C.TEXT_DIM)

        # Button states
        if self._current_step == 0:
            self._back_btn.configure(state="disabled")
        else:
            self._back_btn.configure(state="normal")

        if self._current_step == len(STEPS) - 1:
            self._next_btn.configure(
                text="Done!",
                fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            )
        else:
            self._next_btn.configure(
                text="Next",
                fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
            )

    def _next_step(self):
        if self._current_step < len(STEPS) - 1:
            self._current_step += 1
            self._show_step()
        else:
            self._close()

    def _prev_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._show_step()

    def _on_checkbox_toggle(self):
        self._config["show_setup_guide"] = not self._dont_show_var.get()

    def _close(self):
        self._config["show_setup_guide"] = not self._dont_show_var.get()
        if self._on_close:
            self._on_close()
        self.grab_release()
        self.destroy()
