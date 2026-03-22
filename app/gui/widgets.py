import customtkinter as ctk
import app.gui.theme as theme
from app.gui.theme import C, F, card


class StatusIndicator(ctk.CTkFrame):
    """A small colored circle indicator (green/yellow/red/gray)."""

    COLORS = {
        "green": C.SUCCESS,
        "yellow": C.WARNING,
        "red": C.ERROR,
        "gray": C.TEXT_DIM,
    }

    def __init__(self, master, color="gray", size=14, **kwargs):
        super().__init__(master, width=size, height=size, corner_radius=size // 2, **kwargs)
        self.configure(fg_color=self.COLORS.get(color, color))
        self._size = size

    def set_color(self, color: str):
        self.configure(fg_color=self.COLORS.get(color, color))


class InfoLabel(ctk.CTkLabel):
    """A multi-line label styled for descriptions/help text."""

    def __init__(self, master, text="", **kwargs):
        kwargs.setdefault("font", F.BODY_SM)
        kwargs.setdefault("text_color", C.TEXT_SEC)
        kwargs.setdefault("justify", "left")
        kwargs.setdefault("anchor", "w")
        kwargs.setdefault("wraplength", theme.WRAP_CONTENT)
        super().__init__(master, text=text, **kwargs)


class SectionHeader(ctk.CTkLabel):
    """A bold section header label."""

    def __init__(self, master, text="", **kwargs):
        kwargs.setdefault("font", F.HEADING)
        kwargs.setdefault("text_color", C.TEXT)
        kwargs.setdefault("anchor", "w")
        super().__init__(master, text=text, **kwargs)


class CardFrame(ctk.CTkFrame):
    """A rounded card panel with the theme card background."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", C.BG_CARD)
        kwargs.setdefault("corner_radius", 12)
        super().__init__(master, **kwargs)


class LogViewer(ctk.CTkTextbox):
    """A read-only scrollable log viewer."""

    def __init__(self, master, height=120, **kwargs):
        super().__init__(
            master, height=height, state="disabled",
            font=F.MONO_SM, fg_color=C.BG_INPUT,
            text_color=C.TEXT_SEC, corner_radius=8, **kwargs,
        )

    def append(self, text: str):
        self.configure(state="normal")
        self.insert("end", text + "\n")
        self.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
