"""
BetterTTS — Centralized UI theme.

All colors, fonts, and button presets live here so every tab
and widget draws from one consistent palette.
"""

import customtkinter as ctk

# ── Screen-aware scaling ────────────────────────────────────
# Set once at startup by apply_window_theme().  Other modules
# read these to compute wraplengths, widget widths, etc.

UI_SCALE: float = 1.0        # overall multiplier (< 1 on small screens)
WRAP_CONTENT: int = 600       # wraplength for body text inside cards
WRAP_WIDE: int = 700          # wraplength for full-width labels (gpu bar)


def _s(px: int) -> int:
    """Scale a pixel value by the current UI_SCALE."""
    return int(px * UI_SCALE)


# ── Colour palette ──────────────────────────────────────────
class C:
    """Colour constants (deep-navy / purple dark theme)."""

    # Backgrounds
    BG_DARK      = "#0f172a"   # main window
    BG_CARD      = "#1e293b"   # card / section panels
    BG_CARD_ALT  = "#162032"   # alternate card shade
    BG_INPUT     = "#334155"   # input fields / textboxes
    BG_HOVER     = "#1a2744"   # subtle hover

    # Accent
    ACCENT       = "#7c3aed"   # primary purple
    ACCENT_HOVER = "#6d28d9"
    ACCENT_LIGHT = "#a78bfa"   # lighter purple for highlights

    # Status
    SUCCESS      = "#10b981"
    SUCCESS_DIM  = "#059669"
    WARNING      = "#f59e0b"
    WARNING_DIM  = "#d97706"
    ERROR        = "#ef4444"
    ERROR_DIM    = "#dc2626"

    # Text
    TEXT         = "#e2e8f0"   # primary text
    TEXT_SEC     = "#94a3b8"   # secondary / muted
    TEXT_DIM     = "#64748b"   # very muted (captions)

    # Misc
    LINK         = "#60a5fa"
    BORDER       = "#1e3a5f"
    SEPARATOR    = "#2d3a4f"


# ── Fonts ───────────────────────────────────────────────────
class F:
    """Font tuples.  Usage: font=F.HEADING"""

    TITLE      = ("Segoe UI", 20, "bold")
    HEADING_LG = ("Segoe UI", 16, "bold")
    HEADING    = ("Segoe UI", 14, "bold")
    BODY       = ("Segoe UI", 13)
    BODY_SM    = ("Segoe UI", 12)
    CAPTION    = ("Segoe UI", 11)
    MONO       = ("Cascadia Code", 13)
    MONO_SM    = ("Cascadia Code", 11)


# ── Button style dicts ──────────────────────────────────────
# Pass these as **kwargs to CTkButton:  CTkButton(..., **BTN_PRIMARY)

BTN_PRIMARY = dict(
    fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
    text_color="#ffffff", corner_radius=8,
)

BTN_SUCCESS = dict(
    fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
    text_color="#ffffff", corner_radius=8,
)

BTN_DANGER = dict(
    fg_color=C.ERROR_DIM, hover_color=C.ERROR,
    text_color="#ffffff", corner_radius=8,
)

BTN_SECONDARY = dict(
    fg_color="#334155", hover_color="#475569",
    text_color=C.TEXT_SEC, corner_radius=8,
)

BTN_GHOST = dict(
    fg_color="transparent", hover_color="#1e293b",
    text_color=C.TEXT_SEC, corner_radius=8,
)


# ── Helper widgets / factories ──────────────────────────────

def card(parent, **kw) -> ctk.CTkFrame:
    """Return a styled card frame (rounded, bg_card)."""
    kw.setdefault("fg_color", C.BG_CARD)
    kw.setdefault("corner_radius", 12)
    return ctk.CTkFrame(parent, **kw)


def separator(parent) -> ctk.CTkFrame:
    """A thin horizontal separator line."""
    sep = ctk.CTkFrame(parent, height=1, fg_color=C.SEPARATOR)
    return sep


def apply_window_theme(window: ctk.CTk):
    """Apply the global dark theme and screen-aware scaling."""
    global UI_SCALE, WRAP_CONTENT, WRAP_WIDE

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Detect screen resolution and compute a comfortable window size
    window.update_idletasks()
    scr_w = window.winfo_screenwidth()
    scr_h = window.winfo_screenheight()

    # Target: 760x680 on a 1920x1080 screen, scale proportionally
    base_w, base_h = 760, 680
    ref_w, ref_h = 1920, 1080

    # Scale factor based on the smaller axis ratio (don't exceed 1.4x)
    scale_w = scr_w / ref_w
    scale_h = scr_h / ref_h
    UI_SCALE = min(scale_w, scale_h, 1.4)

    # On very small screens (< 1280 wide) shrink below 1.0
    if UI_SCALE < 0.75:
        UI_SCALE = 0.75

    win_w = int(base_w * UI_SCALE)
    win_h = int(base_h * UI_SCALE)

    # Center the window on screen
    x = (scr_w - win_w) // 2
    y = (scr_h - win_h) // 2
    window.geometry(f"{win_w}x{win_h}+{x}+{y}")
    window.minsize(int(600 * UI_SCALE), int(480 * UI_SCALE))

    # Apply customtkinter's built-in widget scaling for DPI awareness
    ctk.set_widget_scaling(UI_SCALE)

    # Update dynamic wraplengths
    WRAP_CONTENT = int(600 * UI_SCALE)
    WRAP_WIDE = int(700 * UI_SCALE)

    window.configure(fg_color=C.BG_DARK)
