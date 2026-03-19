"""
gui/tabs/sensitivity.py
────────────────────────
Receiver Sensitivity vs Bandwidth tab.

INTERACTIVE FEATURES:
  • NF slider → sensitivity curve shifts live.
  • SNR_req slider → shifts the entire family of curves up/down together.
  • Temperature slider → noise floor shifts (physical effect visible instantly).
  • BW operating point slider → vertical marker sweeps to show exact sensitivity.
  • "Add NF curve" button overlays the current NF curve for comparison.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.gridspec as gridspec

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import core
from gui.theme   import (BG, CARD, PANEL, ACCENT, ACCENT2, WARN,
                          TEXT, TEXT_DIM, FONT_HEAD, FONT_BODY, FONT_SMALL,
                          FONT_VALUE, COLORS)
from gui.widgets import LiveSlider, ResultCard, SectionFrame, PlotCanvas


class SensitivityTab(tk.Frame):

    DEBOUNCE_MS = 100

    def __init__(self, parent, defaults: dict, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._d        = defaults
        self._job      = None
        self._overlays: list = []   # list of (nf, snr, temp, label)
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

        self._canvas = PlotCanvas(self._right, figsize=(9.5, 5.0))
        self._canvas.pack(fill="both", expand=True)

    def _build_controls(self):
        d = self._d

        def sl(parent, lbl, lo, hi, val, unit, res=0.5):
            s = LiveSlider(parent, lbl, lo, hi, val, unit,
                           resolution=res, on_change=self._schedule)
            s.pack(fill="x", pady=2, padx=4)
            return s

        # Primary sliders
        pf = SectionFrame(self._left, "Receiver Parameters")
        pf.pack(fill="x", pady=(0, 6))
        self._nf      = sl(pf, "Noise Figure",    0,   25, 5.0,    "dB",  0.1)
        self._snr_req = sl(pf, "Required SNR",    0,   30, d.get("snr_req_db", 10), "dB", 0.5)
        self._temp    = sl(pf, "Temperature",     77, 400, d.get("temp_k", 290), "K",   1)

        # Operating point
        op = SectionFrame(self._left, "⬤  BW Operating Point")
        op.pack(fill="x", pady=(0, 6))
        self._bw_op   = sl(op, "Channel Bandwidth", 0.01, 500, 20, "MHz", 1)
        tk.Label(op, text="← shows sensitivity at this BW",
                 bg=CARD, fg=TEXT_DIM, font=FONT_SMALL).pack(padx=8, pady=(0, 6))

        # Live result cards
        cf = tk.Frame(self._left, bg=BG)
        cf.pack(fill="x", pady=(0, 6))
        self._card_sens   = ResultCard(cf, "Sensitivity @ BW op.", "dBm")
        self._card_sens.pack(fill="x", pady=2)
        self._card_floor  = ResultCard(cf, "Thermal Noise Floor", "dBm")
        self._card_floor.pack(fill="x", pady=2)

        # Compare overlays
        ov = SectionFrame(self._left, "Compare")
        ov.pack(fill="x", pady=(0, 6))
        ttk.Button(ov, text="📌 Add Current NF Curve",
                   command=self._save_overlay).pack(fill="x", padx=6, pady=3)
        ttk.Button(ov, text="✕ Clear Overlays",
                   command=self._clear_overlays,
                   style="Secondary.TButton").pack(fill="x", padx=6, pady=3)

        # NF sweep controls
        sf = SectionFrame(self._left, "NF Sweep (multi-curve)")
        sf.pack(fill="x", pady=(0, 4))
        tk.Label(sf, text="NF values (comma-sep):", bg=CARD, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(anchor="w", padx=8, pady=(4, 0))
        self._nf_sweep_var = tk.StringVar(value="2,5,8,12,18")
        ttk.Entry(sf, textvariable=self._nf_sweep_var, width=22).pack(
            padx=8, pady=(2, 6))
        self._nf_sweep_var.trace_add("write", self._schedule)

    def _schedule(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self.DEBOUNCE_MS, self._redraw)

    def _redraw(self):
        nf      = self._nf.get()
        snr_req = self._snr_req.get()
        temp    = self._temp.get()
        bw_op   = self._bw_op.get() * 1e6   # Hz

        try:
            nf_sweep = [float(x.strip())
                        for x in self._nf_sweep_var.get().split(",")
                        if x.strip()]
        except ValueError:
            nf_sweep = [5.0]

        bw_hz   = np.logspace(3, np.log10(1e9), 400)   # 1 kHz → 1 GHz
        bw_mhz  = bw_hz / 1e6
        floor   = core.thermal_noise_dbm(bw_hz, temp)

        # Live KPI
        sens_at_op = core.receiver_sensitivity_dbm(bw_op, nf, snr_req, temp)
        floor_at_op = core.thermal_noise_dbm(bw_op, temp)
        self._card_sens.update(sens_at_op)
        self._card_floor.update(floor_at_op)

        # ── Plot ──
        fig = self._canvas.figure
        fig.clear()
        gs  = gridspec.GridSpec(1, 2, figure=fig, wspace=0.35)
        ax1 = fig.add_subplot(gs[0]); ax1.set_facecolor(PANEL)
        ax2 = fig.add_subplot(gs[1]); ax2.set_facecolor(PANEL)

        # Left: NF sweep family
        for nf_val, clr in zip(nf_sweep, COLORS):
            s = core.receiver_sensitivity_dbm(bw_hz, nf_val, snr_req, temp)
            ax1.plot(bw_mhz, s, color=clr, lw=1.8, label=f"NF={nf_val:.0f}dB")

        # Overlays
        for (onf, osnr, otemp, olbl) in self._overlays:
            s_ov = core.receiver_sensitivity_dbm(bw_hz, onf, osnr, otemp)
            ax1.plot(bw_mhz, s_ov, color=TEXT_DIM, lw=1.2, ls="--",
                      alpha=0.5, label=olbl)

        ax1.plot(bw_mhz, floor, color=TEXT_DIM, lw=1.5, ls=":",
                  label="kTB floor")
        ax1.axvline(bw_op / 1e6, color=ACCENT2, lw=1.8, ls="--",
                    label=f"BW={bw_op/1e6:.1f}MHz")
        ax1.axhline(sens_at_op, color=ACCENT, lw=1.2, ls=":",
                    alpha=0.7, label=f"Sens={sens_at_op:.1f}dBm")

        # Operating point marker on the active NF curve
        ax1.plot(bw_op / 1e6, sens_at_op, "o", color=ACCENT2,
                  ms=10, zorder=5, markeredgecolor=BG, markeredgewidth=1.5)

        ax1.set_xscale("log"); ax1.invert_yaxis()
        ax1.set_xlabel("Bandwidth [MHz]")
        ax1.set_ylabel("Sensitivity [dBm]")
        ax1.set_title(f"Sensitivity vs BW  (SNR={snr_req:.0f}dB, T={temp:.0f}K)",
                       color=TEXT)
        ax1.legend(fontsize=8, framealpha=0.8)

        # Right: temperature effect on noise floor
        temps  = np.linspace(77, 500, 400)   # K
        bw_ref = bw_op
        sens_vs_temp = core.receiver_sensitivity_dbm(bw_ref, nf, snr_req, temps)
        ax2.plot(temps, sens_vs_temp, color=ACCENT, lw=2.2)
        ax2.axvline(temp, color=ACCENT2, lw=2, ls="--",
                    label=f"T={temp:.0f} K")
        ax2.axhline(sens_at_op, color=ACCENT2, lw=1.2, ls=":",
                    alpha=0.7)
        ax2.plot(temp, sens_at_op, "o", color=ACCENT2,
                  ms=10, zorder=5, markeredgecolor=BG, markeredgewidth=1.5)
        ax2.set_xlabel("System Temperature [K]")
        ax2.set_ylabel("Sensitivity [dBm]")
        ax2.set_title(f"Sensitivity vs Temperature\n"
                       f"(BW={bw_op/1e6:.1f}MHz, NF={nf:.1f}dB)",
                       color=TEXT)
        ax2.invert_yaxis()
        ax2.legend(fontsize=9, framealpha=0.8)
        # Mark standard temperatures
        for t_ref, lbl in [(290, "T_std"), (293, "Room"), (77, "LN₂")]:
            ax2.axvline(t_ref, color=TEXT_DIM, lw=0.8, ls=":", alpha=0.5)
            ax2.text(t_ref + 2, ax2.get_ylim()[0] if ax2.get_ylim() else -100,
                      lbl, fontsize=7, color=TEXT_DIM, rotation=90, va="bottom")

        self._canvas.redraw()

    def _save_overlay(self):
        nf      = self._nf.get()
        snr_req = self._snr_req.get()
        temp    = self._temp.get()
        lbl     = f"NF={nf:.0f}dB SNR={snr_req:.0f}dB T={temp:.0f}K"
        self._overlays.append((nf, snr_req, temp, lbl))
        self._redraw()

    def _clear_overlays(self):
        self._overlays.clear()
        self._redraw()
