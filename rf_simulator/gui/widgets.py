"""
gui/widgets.py
───────────────
Reusable, self-contained widgets shared across all tabs.

Key widgets:
  • LiveSlider     — slider + numeric entry, bidirectionally linked,
                     calls on_change(value) on every movement
  • ResultCard     — coloured metric display card
  • SectionFrame   — labelled card frame
  • PlotCanvas     — matplotlib Figure embedded in Tk with toolbar
  • StageRow       — one row in the cascaded-chain editor
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from gui.theme import (BG, CARD, PANEL, BORDER, ACCENT, ACCENT2, WARN,
                        TEXT, TEXT_DIM, ENTRY_BG, FONT_BODY, FONT_HEAD,
                        FONT_SMALL, FONT_VALUE, FONT_RESULT)


# ── LiveSlider ────────────────────────────────────────────────────────────────

class LiveSlider(tk.Frame):
    """
    A slider+entry pair that stay in sync.

    on_change(float_value) is called immediately whenever the value moves —
    the tab wires this to a debounced redraw, giving real-time feedback.
    """

    def __init__(self, parent,
                 label: str,
                 from_: float, to: float,
                 default: float,
                 unit: str = "",
                 resolution: float = 0.1,
                 on_change: Optional[Callable] = None,
                 **kwargs):
        super().__init__(parent, bg=CARD, **kwargs)
        self._on_change = on_change
        self._var = tk.DoubleVar(value=default)
        self._updating = False   # guard against recursive callbacks

        # ── label ──
        lbl_frame = tk.Frame(self, bg=CARD)
        lbl_frame.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(lbl_frame, text=label, bg=CARD, fg=TEXT_DIM,
                 font=FONT_BODY, anchor="w").pack(side="left")
        self._unit_lbl = tk.Label(lbl_frame, text=unit, bg=CARD,
                                   fg=TEXT_DIM, font=FONT_SMALL)
        self._unit_lbl.pack(side="right")

        # ── slider + entry row ──
        ctrl = tk.Frame(self, bg=CARD)
        ctrl.pack(fill="x", padx=8, pady=(0, 4))

        self._slider = ttk.Scale(ctrl, from_=from_, to=to,
                                  variable=self._var,
                                  orient="horizontal",
                                  command=self._slider_moved)
        self._slider.pack(side="left", fill="x", expand=True)

        self._entry = ttk.Entry(ctrl, width=8,
                                 textvariable=self._var)
        self._entry.pack(side="left", padx=(6, 0))
        self._entry.bind("<Return>",   self._entry_committed)
        self._entry.bind("<FocusOut>", self._entry_committed)

        # live value display
        self._val_lbl = tk.Label(ctrl, text=f"{default:.2f}",
                                  bg=CARD, fg=ACCENT, font=FONT_VALUE, width=8)
        self._val_lbl.pack(side="left", padx=(4, 0))

        self._from = from_
        self._to   = to

    def _slider_moved(self, _=None):
        if self._updating:
            return
        v = self._var.get()
        self._val_lbl.config(text=f"{v:.2f}")
        if self._on_change:
            self._on_change(v)

    def _entry_committed(self, _=None):
        try:
            v = float(self._entry.get())
            v = max(self._from, min(self._to, v))
        except ValueError:
            return
        self._updating = True
        self._var.set(v)
        self._val_lbl.config(text=f"{v:.2f}")
        self._updating = False
        if self._on_change:
            self._on_change(v)

    def get(self) -> float:
        return self._var.get()

    def set(self, value: float):
        self._var.set(value)
        self._val_lbl.config(text=f"{value:.2f}")


# ── ResultCard ────────────────────────────────────────────────────────────────

class ResultCard(tk.Frame):
    """
    Compact coloured metric card  ┌─────────────┐
                                  │  Label       │
                                  │  VALUE  unit │
                                  │  status msg  │
                                  └─────────────┘
    """

    def __init__(self, parent, label: str, unit: str = "", **kwargs):
        super().__init__(parent, bg=CARD, bd=1, relief="solid",
                          highlightbackground=BORDER, highlightthickness=1,
                          **kwargs)
        tk.Label(self, text=label, bg=CARD, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(pady=(6, 0), padx=10, anchor="w")
        self._val_lbl = tk.Label(self, text="—", bg=CARD, fg=ACCENT,
                                  font=FONT_RESULT)
        self._val_lbl.pack(padx=10, pady=(0, 2))
        self._unit_lbl = tk.Label(self, text=unit, bg=CARD, fg=TEXT_DIM,
                                   font=FONT_SMALL)
        self._unit_lbl.pack(pady=(0, 4), padx=10)
        self._status = tk.Label(self, text="", bg=CARD, font=FONT_SMALL)
        self._status.pack(pady=(0, 6))

    def update(self, value: float, status: str = "", good: Optional[bool] = None):
        color = ACCENT
        if good is True:
            color = ACCENT2
        elif good is False:
            color = WARN
        self._val_lbl.config(text=f"{value:.2f}", fg=color)
        sc = ACCENT2 if good is True else (WARN if good is False else TEXT_DIM)
        self._status.config(text=status, fg=sc)


# ── SectionFrame ─────────────────────────────────────────────────────────────

class SectionFrame(tk.LabelFrame):
    """Styled labelled card frame."""

    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent,
                         text=f"  {title}  ",
                         bg=CARD, fg=ACCENT,
                         font=FONT_HEAD,
                         bd=1, relief="solid",
                         labelanchor="nw",
                         **kwargs)


# ── PlotCanvas ────────────────────────────────────────────────────────────────

class PlotCanvas(tk.Frame):
    """
    A matplotlib Figure embedded in a Tk Frame with an optional toolbar.

    Usage:
        canvas = PlotCanvas(parent, figsize=(8, 4))
        ax = canvas.ax         # primary axes
        # ... draw on ax ...
        canvas.redraw()        # efficient repaint

    For multi-axes layouts, pass subplot_kw or use canvas.figure directly.
    """

    def __init__(self, parent, figsize=(9, 4.5), toolbar=True, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.figure = Figure(figsize=figsize, facecolor=BG)
        self.ax     = self.figure.add_subplot(111)
        self.ax.set_facecolor(PANEL)

        self._canvas = FigureCanvasTkAgg(self.figure, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        if toolbar:
            self._toolbar = NavigationToolbar2Tk(self._canvas, self)
            self._toolbar.config(background=PANEL)
            self._toolbar.update()

    def redraw(self):
        """Efficient repaint without rebuilding the figure."""
        self._canvas.draw_idle()

    def clear(self):
        """Clear all axes and reset."""
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(PANEL)

    def add_axes(self, *args, **kwargs):
        """Proxy to figure.add_subplot for multi-panel layouts."""
        ax = self.figure.add_subplot(*args, **kwargs)
        ax.set_facecolor(PANEL)
        return ax


# ── StageRow (for cascaded chain editor) ─────────────────────────────────────

class StageRow(tk.Frame):
    """
    One stage row in the cascaded chain editor.
    Fields: index (read-only), name, gain, NF, OIP3.
    Calls on_change() whenever any field is edited.
    """

    def __init__(self, parent, idx: int, defaults: dict,
                 on_change: Optional[Callable] = None,
                 alt: bool = False, **kwargs):
        bg = CARD if not alt else PANEL
        super().__init__(parent, bg=bg, **kwargs)
        self._on_change = on_change

        tk.Label(self, text=f"{idx}", bg=bg, fg=TEXT_DIM,
                 font=FONT_BODY, width=4, anchor="center").pack(side="left", padx=4)

        self._vars: dict[str, tk.StringVar] = {}
        fields = [
            ("name",    defaults.get("name",    f"Stage {idx}"), 12),
            ("gain_db", str(defaults.get("gain_db", 0.0)),       8),
            ("nf_db",   str(defaults.get("nf_db",   3.0)),       8),
            ("oip3_dbm",str(defaults.get("oip3_dbm",25.0)),      8),
        ]
        for key, val, width in fields:
            v = tk.StringVar(value=val)
            v.trace_add("write", self._changed)
            e = ttk.Entry(self, textvariable=v, width=width)
            e.pack(side="left", padx=4, pady=3)
            self._vars[key] = v

    def _changed(self, *_):
        if self._on_change:
            self._on_change()

    def get(self) -> dict:
        try:
            return {
                "name":     self._vars["name"].get(),
                "gain_db":  float(self._vars["gain_db"].get()),
                "nf_db":    float(self._vars["nf_db"].get()),
                "oip3_dbm": float(self._vars["oip3_dbm"].get()),
            }
        except ValueError:
            return None   # caller handles invalid input
