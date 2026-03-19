"""
gui/tabs/path_loss.py
──────────────────────
Path Loss Models tab.

INTERACTIVE FEATURES:
  • Frequency slider → all curves update live (you can see models
    "validity regions" shift as you cross 1500 MHz from OH to COST-231).
  • Distance range sliders (min/max) → axes zoom live.
  • Antenna height sliders → real-time curve change.
  • Model checkboxes → toggle curves without recalculating everything.
  • Vertical marker shows operating point from Link Budget tab.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import core
from core.path_loss import MODEL_REGISTRY
from gui.theme   import (BG, CARD, PANEL, ACCENT, ACCENT2, WARN,
                          TEXT, TEXT_DIM, FONT_HEAD, FONT_BODY, FONT_SMALL,
                          COLORS)
from gui.widgets import LiveSlider, SectionFrame, PlotCanvas


_LINE_STYLES = ["-", "--", "-.", ":", "-", "--"]


class PathLossTab(tk.Frame):

    DEBOUNCE_MS = 100

    def __init__(self, parent, defaults: dict, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._d   = defaults
        self._job = None
        self._build()
        self._redraw()

    def _build(self):
        self._left = tk.Frame(self, bg=BG, width=290)
        self._left.pack(side="left", fill="y", padx=(10, 6), pady=10)
        self._left.pack_propagate(False)

        self._right = tk.Frame(self, bg=BG)
        self._right.pack(side="left", fill="both", expand=True,
                          padx=(0, 10), pady=10)

        self._build_controls()

        self._canvas = PlotCanvas(self._right, figsize=(9.5, 5.5))
        self._canvas.pack(fill="both", expand=True)

    def _build_controls(self):
        d = self._d

        def sl(parent, lbl, lo, hi, val, unit, res=1.0):
            s = LiveSlider(parent, lbl, lo, hi, val, unit,
                           resolution=res, on_change=self._schedule)
            s.pack(fill="x", pady=2, padx=4)
            return s

        # Parameters
        pf = SectionFrame(self._left, "Parameters")
        pf.pack(fill="x", pady=(0, 6))
        self._freq  = sl(pf, "Frequency",     100, 2000, d.get("freq_mhz", 1800),  "MHz", 10)
        self._d_min = sl(pf, "Distance Min",  0.1,   5,  d.get("d_min_km", 0.1), "km",  0.1)
        self._d_max = sl(pf, "Distance Max",  1,   100,  d.get("d_max_km", 20), "km",  1)
        self._h_bs  = sl(pf, "BS Height",     10,  200,  d.get("h_bs_m", 30),   "m",   1)
        self._h_ms  = sl(pf, "MS Height",     1,    10,  d.get("h_ms_m", 1.5),   "m",   0.5)

        # Model toggles
        mf = SectionFrame(self._left, "Models")
        mf.pack(fill="x", pady=(0, 6))
        self._model_vars: dict[str, tk.BooleanVar] = {}
        default_on = {"Free Space", "Okumura-Hata Urban",
                      "Okumura-Hata Suburban", "COST-231 Medium City"}
        for name in MODEL_REGISTRY:
            v = tk.BooleanVar(value=(name in default_on))
            v.trace_add("write", self._schedule)
            cb = tk.Checkbutton(mf, text=name, variable=v,
                                 bg=CARD, fg=TEXT, activebackground=CARD,
                                 selectcolor=CARD, font=FONT_BODY)
            cb.pack(anchor="w", padx=8, pady=1)
            self._model_vars[name] = v

        # Validity hint label
        self._hint = tk.Label(self._left, text="", bg=BG, fg=WARN,
                               font=FONT_SMALL, wraplength=270, justify="left")
        self._hint.pack(padx=8, pady=4, anchor="w")

    def _schedule(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self.DEBOUNCE_MS, self._redraw)

    def _redraw(self):
        freq_mhz = self._freq.get()
        d_min    = self._d_min.get()
        d_max    = max(self._d_max.get(), d_min + 0.5)
        h_bs     = self._h_bs.get()
        h_ms     = self._h_ms.get()
        freq_hz  = freq_mhz * 1e6

        d_km = np.logspace(np.log10(d_min), np.log10(d_max), 300)

        params = {"freq_hz": freq_hz, "freq_mhz": freq_mhz,
                  "h_bs": h_bs, "h_ms": h_ms}

        # Validity warnings
        hints = []
        if freq_mhz < 150:
            hints.append("⚠ <150 MHz: O-H not valid")
        if freq_mhz > 1500:
            hints.append("⚠ >1500 MHz: O-H extrapolated")
        if freq_mhz < 1500:
            hints.append("ℹ <1500 MHz: COST-231 clamped")
        self._hint.config(text="  ".join(hints))

        ax = self._canvas.figure.clear() or None
        ax = self._canvas.figure.add_subplot(111)
        ax.set_facecolor(PANEL)

        plotted = 0
        for (name, meta), clr, ls in zip(
                MODEL_REGISTRY.items(), COLORS, _LINE_STYLES):
            if not self._model_vars[name].get():
                continue
            try:
                pl = meta["fn"](params, d_km)
                ax.plot(d_km, pl, color=clr, ls=ls, lw=2.2, label=name)
                plotted += 1
            except Exception:
                pass

        if plotted == 0:
            ax.text(0.5, 0.5, "Select at least one model",
                    transform=ax.transAxes, ha="center", va="center",
                    color=TEXT_DIM, fontsize=12)

        ax.set_xscale("log")
        ax.set_xlabel("Distance [km]")
        ax.set_ylabel("Path Loss [dB]")
        ax.set_title(f"Path Loss @ {freq_mhz:.0f} MHz  "
                     f"(h_BS={h_bs:.0f}m, h_MS={h_ms:.1f}m)",
                     color=TEXT)
        ax.legend(fontsize=9, framealpha=0.8)
        ax.grid(True, which="both", ls="--", alpha=0.3)

        self._canvas.redraw()
