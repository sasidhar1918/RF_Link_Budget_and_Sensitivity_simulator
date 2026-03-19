"""
gui/tabs/ber_plots.py
──────────────────────
BER vs SNR tab.

INTERACTIVE FEATURES:
  • SNR operating-point slider → a live vertical marker sweeps across all
    curves simultaneously, showing each modulation's BER at that exact SNR.
  • Live readout panel shows BER value per modulation at the current SNR.
  • Modulation checkboxes toggle curves instantly (no recalculate button).
  • SNR range sliders change axis limits live.
  • "Required SNR for BER target" table updates as modulations are toggled.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import core
from core.modulation import MODULATIONS, snr_for_ber_target
from gui.theme   import (BG, CARD, PANEL, ACCENT, ACCENT2, WARN,
                          TEXT, TEXT_DIM, FONT_HEAD, FONT_BODY, FONT_SMALL,
                          FONT_VALUE, COLORS)
from gui.widgets import LiveSlider, SectionFrame, PlotCanvas


class BERPlotsTab(tk.Frame):

    DEBOUNCE_MS = 80   # BER is cheap — update fast

    def __init__(self, parent, defaults: dict, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._d   = defaults
        self._job = None
        self._build()
        self._redraw()

    def _build(self):
        self._left = tk.Frame(self, bg=BG, width=270)
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

        def sl(parent, lbl, lo, hi, val, unit, res=0.5):
            s = LiveSlider(parent, lbl, lo, hi, val, unit,
                           resolution=res, on_change=self._schedule)
            s.pack(fill="x", pady=2, padx=4)
            return s

        # Range
        rf = SectionFrame(self._left, "SNR Range")
        rf.pack(fill="x", pady=(0, 6))
        self._snr_min = sl(rf, "SNR Min",  0,  5, d.get("snr_min_db", 0), "dB", 0.5)
        self._snr_max = sl(rf, "SNR Max", 10, 40, d.get("snr_max_db", 30), "dB", 0.5)

        # Operating point — this is the KEY interactive element
        op = SectionFrame(self._left, "⬤  Operating Point")
        op.pack(fill="x", pady=(0, 6))
        self._snr_op = sl(op, "Current SNR", 0, 40, 15, "dB", 0.5)
        tk.Label(op, text="← drag to see BER at each modulation",
                 bg=CARD, fg=TEXT_DIM, font=FONT_SMALL,
                 wraplength=240, justify="left").pack(padx=8, pady=(0, 6))

        # Live BER readout per modulation at operating point
        self._readout_frame = SectionFrame(self._left, "BER @ operating point")
        self._readout_frame.pack(fill="x", pady=(0, 6))
        self._readout_labels: dict[str, tk.Label] = {}
        for mod in MODULATIONS:
            fr = tk.Frame(self._readout_frame, bg=CARD)
            fr.pack(fill="x", padx=6, pady=1)
            tk.Label(fr, text=mod, bg=CARD, fg=TEXT_DIM,
                     font=FONT_SMALL, width=8, anchor="w").pack(side="left")
            lbl = tk.Label(fr, text="—", bg=CARD, fg=ACCENT, font=FONT_VALUE)
            lbl.pack(side="right")
            self._readout_labels[mod] = lbl

        # Modulation toggles
        mf = SectionFrame(self._left, "Modulations")
        mf.pack(fill="x", pady=(0, 6))
        self._mod_vars: dict[str, tk.BooleanVar] = {}
        defaults_on = {"BPSK","QPSK","16QAM","64QAM","256QAM"}
        for mod in MODULATIONS:
            v = tk.BooleanVar(value=(mod in defaults_on))
            v.trace_add("write", self._schedule)
            tk.Checkbutton(mf, text=mod, variable=v,
                           bg=CARD, fg=TEXT, activebackground=CARD,
                           selectcolor=CARD, font=FONT_BODY).pack(
                           anchor="w", padx=8, pady=1)
            self._mod_vars[mod] = v

        # Reference table
        tk.Label(self._left, text="SNR required (dB):",
                 bg=BG, fg=TEXT_DIM, font=FONT_SMALL).pack(anchor="w", padx=6, pady=(4, 0))
        self._snr_table = ttk.Treeview(
            self._left,
            columns=("Mod", "BER=10⁻³", "BER=10⁻⁶"),
            show="headings", height=7)
        for c, w in [("Mod", 70), ("BER=10⁻³", 80), ("BER=10⁻⁶", 80)]:
            self._snr_table.heading(c, text=c)
            self._snr_table.column(c, width=w, anchor="center")
        self._snr_table.pack(fill="x", padx=6, pady=4)

    def _schedule(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self.DEBOUNCE_MS, self._redraw)

    def _redraw(self):
        s_min  = self._snr_min.get()
        s_max  = max(self._snr_max.get(), s_min + 5)
        s_op   = self._snr_op.get()

        snr_db  = np.linspace(s_min, s_max, 600)
        snr_lin = 10 ** (snr_db / 10)
        op_lin  = 10 ** (s_op / 10)

        ax = self._canvas.figure.clear() or None
        ax = self._canvas.figure.add_subplot(111)
        ax.set_facecolor(PANEL)

        for (mod, checked), clr, ls in zip(
                self._mod_vars.items(), COLORS,
                ["-", "--", "-.", ":", "-", "--"]):
            if not checked.get():
                self._readout_labels[mod].config(text="—", fg=TEXT_DIM)
                continue
            ber_curve = core.ber_vs_snr(snr_lin, mod)
            ax.semilogy(snr_db, ber_curve, color=clr, ls=ls,
                         lw=2.2, label=mod, zorder=3)

            # Operating point marker on each active curve
            ber_at_op = float(core.ber_vs_snr(np.array([op_lin]), mod)[0])
            if 1e-12 < ber_at_op < 1:
                ax.plot(s_op, ber_at_op, "o", color=clr, ms=9,
                         zorder=5, markeredgecolor=BG, markeredgewidth=1.5)
                ax.annotate(f"{ber_at_op:.1e}",
                            xy=(s_op, ber_at_op),
                            xytext=(4, 4), textcoords="offset points",
                            fontsize=7.5, color=clr)
            # Live BER readout
            self._readout_labels[mod].config(
                text=f"{ber_at_op:.2e}", fg=clr)

        # Operating SNR vertical line
        ax.axvline(s_op, color=ACCENT2, lw=1.8, ls="--",
                    label=f"Operating SNR = {s_op:.1f} dB", zorder=4)

        # Reference BER lines
        for ber_ref, lbl in [(1e-3, "10⁻³"), (1e-6, "10⁻⁶"), (1e-9, "10⁻⁹")]:
            ax.axhline(ber_ref, color=TEXT_DIM, lw=1, ls=":", alpha=0.5)
            ax.text(s_max + 0.1, ber_ref, lbl, color=TEXT_DIM,
                     fontsize=7.5, va="center")

        ax.set_xlabel("Es/N₀ [dB]")
        ax.set_ylabel("Bit Error Rate (BER)")
        ax.set_title("BER vs SNR — Analytical (AWGN)", color=TEXT)
        ax.set_xlim(s_min, s_max + 1)
        ax.set_ylim(1e-12, 1)
        ax.legend(fontsize=9, framealpha=0.8, loc="upper right")
        ax.grid(True, which="both", ls="--", alpha=0.3)

        self._canvas.redraw()

        # Update reference SNR table
        for row in self._snr_table.get_children():
            self._snr_table.delete(row)
        for (mod, checked), clr in zip(self._mod_vars.items(), COLORS):
            if checked.get():
                s3 = snr_for_ber_target(1e-3, mod)
                s6 = snr_for_ber_target(1e-6, mod)
                self._snr_table.insert("", "end",
                    values=(mod, f"{s3:.1f}", f"{s6:.1f}"))
