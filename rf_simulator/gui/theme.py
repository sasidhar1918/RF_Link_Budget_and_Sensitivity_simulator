"""
gui/theme.py
─────────────
Single source of truth for all visual constants.
Change a color here → it updates everywhere.
"""

import tkinter as tk
from tkinter import ttk

# ── Palette ──────────────────────────────────────────────────────────────────
BG        = "#0d1117"
PANEL     = "#161b22"
CARD      = "#1e2530"
BORDER    = "#30363d"
ACCENT    = "#58a6ff"
ACCENT2   = "#3fb950"
ACCENT3   = "#d2a8ff"
WARN      = "#f78166"
TEXT      = "#e6edf3"
TEXT_DIM  = "#8b949e"
ENTRY_BG  = "#0d1117"
SLIDER_BG = "#21262d"

COLORS = [ACCENT, ACCENT2, ACCENT3, "#ffa657", WARN, "#79c0ff"]

# ── Typography ────────────────────────────────────────────────────────────────
FONT_TITLE  = ("Consolas", 17, "bold")
FONT_HEAD   = ("Consolas", 10, "bold")
FONT_BODY   = ("Consolas",  9)
FONT_SMALL  = ("Consolas",  8)
FONT_RESULT = ("Consolas", 13, "bold")
FONT_VALUE  = ("Consolas", 11, "bold")

# ── Matplotlib rcParams ──────────────────────────────────────────────────────
MPL_STYLE = {
    "figure.facecolor":  BG,
    "axes.facecolor":    PANEL,
    "axes.edgecolor":    BORDER,
    "axes.labelcolor":   TEXT,
    "axes.grid":         True,
    "grid.color":        BORDER,
    "grid.linestyle":    "--",
    "grid.alpha":        0.45,
    "text.color":        TEXT,
    "xtick.color":       TEXT_DIM,
    "ytick.color":       TEXT_DIM,
    "legend.facecolor":  CARD,
    "legend.edgecolor":  BORDER,
    "legend.labelcolor": TEXT,
    "lines.linewidth":   2.2,
    "font.family":       "monospace",
}


def apply_ttk_theme(root: tk.Tk) -> None:
    """Apply the dark theme to all ttk widgets."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",
        background=BG, foreground=TEXT,
        fieldbackground=ENTRY_BG, font=FONT_BODY,
        troughcolor=PANEL, bordercolor=BORDER,
        lightcolor=BORDER, darkcolor=BORDER, relief="flat")

    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
    style.configure("TNotebook.Tab",
        background=PANEL, foreground=TEXT_DIM,
        padding=[14, 6], font=FONT_HEAD, borderwidth=0)
    style.map("TNotebook.Tab",
        background=[("selected", CARD)],
        foreground=[("selected", ACCENT)])

    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)

    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Dim.TLabel", background=BG, foreground=TEXT_DIM)
    style.configure("CardDim.TLabel", background=CARD, foreground=TEXT_DIM)

    style.configure("TEntry",
        fieldbackground=ENTRY_BG, foreground=TEXT,
        insertcolor=ACCENT, borderwidth=1)

    style.configure("TButton",
        background=ACCENT, foreground=BG,
        font=FONT_HEAD, padding=[10, 5])
    style.map("TButton", background=[("active", "#79c0ff"), ("pressed", "#1f6feb")])

    style.configure("Secondary.TButton",
        background=CARD, foreground=ACCENT,
        font=FONT_HEAD, padding=[10, 5], borderwidth=1)
    style.map("Secondary.TButton",
        background=[("active", PANEL)])

    style.configure("TCombobox",
        fieldbackground=ENTRY_BG, foreground=TEXT,
        selectbackground=ACCENT, selectforeground=BG)
    style.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG)])

    style.configure("TScale",
        background=BG, troughcolor=SLIDER_BG, sliderlength=16,
        sliderrelief="flat")

    style.configure("TLabelframe",
        background=CARD, foreground=ACCENT,
        bordercolor=BORDER, font=FONT_HEAD)
    style.configure("TLabelframe.Label",
        background=CARD, foreground=ACCENT, font=FONT_HEAD)

    style.configure("Treeview",
        background=CARD, foreground=TEXT,
        fieldbackground=CARD, rowheight=22)
    style.configure("Treeview.Heading",
        background=PANEL, foreground=ACCENT, font=FONT_HEAD)
    style.map("Treeview", background=[("selected", "#1f6feb")])

    style.configure("TCheckbutton",
        background=CARD, foreground=TEXT,
        indicatorcolor=ENTRY_BG, selectcolor=ACCENT)
    style.map("TCheckbutton",
        background=[("active", CARD)],
        foreground=[("active", TEXT)])

    style.configure("TRadiobutton",
        background=CARD, foreground=TEXT)
    style.map("TRadiobutton", background=[("active", CARD)])

    style.configure("TSpinbox",
        fieldbackground=ENTRY_BG, foreground=TEXT,
        insertcolor=ACCENT, arrowcolor=ACCENT)
