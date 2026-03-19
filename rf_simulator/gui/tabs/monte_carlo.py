"""
gui/tabs/monte_carlo.py
────────────────────────
Monte Carlo Fading Simulation tab.

INTERACTIVE FEATURES:
  • Mean Rx Power slider → updates distribution live.
  • Sensitivity threshold slider → outage region shades instantly.
  • K-factor slider (for Rician / Nakagami) → distribution shape changes.
  • Model selector → switch Rayleigh / Rician / Nakagami / AWGN.
  • Overlay mode — run multiple models and compare CDFs side by side.
  • All stats (outage %, mean, std, percentiles) update on each run.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import core
from gui.theme   import (BG, CARD, PANEL, ACCENT, ACCENT2, WARN,
                          TEXT, TEXT_DIM, FONT_HEAD, FONT_BODY, FONT_SMALL,
                          FONT_VALUE, COLORS)
from gui.widgets import LiveSlider, ResultCard, SectionFrame, PlotCanvas


class MonteCarloTab(tk.Frame):

    def __init__(self, parent, defaults: dict, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._d        = defaults
        self._overlays: list = []
        self._build()

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

        def sl(parent, lbl, lo, hi, val, unit, res=1.0):
            s = LiveSlider(parent, lbl, lo, hi, val, unit,
                           resolution=res, on_change=None)   # manual run
            s.pack(fill="x", pady=2, padx=4)
            return s

        pf = SectionFrame(self._left, "Signal Parameters")
        pf.pack(fill="x", pady=(0, 6))
        self._p_rx = sl(pf, "Mean Rx Power",   -120,  0, d.get("mean_rx_dbm", -70),     "dBm", 1)
        self._sens = sl(pf, "Sensitivity",      -120, -20, d.get("sensitivity_dbm", -90), "dBm", 1)
        self._k    = sl(pf, "K / m  factor",    0,   20, d.get("k_factor_db", 6),      "dB",  0.5)

        mf = SectionFrame(self._left, "Fading Model")
        mf.pack(fill="x", pady=(0, 6))
        self._model = tk.StringVar(value="Rayleigh")
        for m in ["Rayleigh", "Rician", "Nakagami", "AWGN"]:
            tk.Radiobutton(mf, text=m, variable=self._model, value=m,
                           bg=CARD, fg=TEXT, activebackground=CARD,
                           selectcolor=CARD, font=FONT_BODY).pack(
                           anchor="w", padx=8, pady=1)

        sf = SectionFrame(self._left, "Samples")
        sf.pack(fill="x", pady=(0, 6))
        self._n_var = tk.StringVar(value="100000")
        fr = tk.Frame(sf, bg=CARD); fr.pack(fill="x", padx=8, pady=6)
        tk.Label(fr, text="N samples:", bg=CARD, fg=TEXT_DIM,
                 font=FONT_BODY).pack(side="left")
        ttk.Combobox(fr, textvariable=self._n_var, width=10,
                     values=["10000","50000","100000","500000"]).pack(
                     side="left", padx=6)

        # Run button (Monte Carlo is heavier — explicit run)
        ttk.Button(self._left, text="▶  Run Simulation",
                   command=self._run).pack(fill="x", pady=6, padx=4)

        # Overlay controls
        of = SectionFrame(self._left, "Compare")
        of.pack(fill="x", pady=(0, 6))
        ttk.Button(of, text="📌 Add to Comparison",
                   command=self._add_overlay).pack(fill="x", padx=6, pady=3)
        ttk.Button(of, text="✕ Clear",
                   command=self._clear_overlays,
                   style="Secondary.TButton").pack(fill="x", padx=6, pady=3)

        # Stats
        sf2 = SectionFrame(self._left, "Statistics")
        sf2.pack(fill="x", pady=(0, 4))
        self._stat_labels: dict[str, tk.Label] = {}
        for stat in ["Outage %", "Mean [dBm]", "Std [dB]", "P10 [dBm]", "P1 [dBm]"]:
            fr2 = tk.Frame(sf2, bg=CARD); fr2.pack(fill="x", padx=8, pady=1)
            tk.Label(fr2, text=stat, bg=CARD, fg=TEXT_DIM,
                     font=FONT_SMALL, width=14, anchor="w").pack(side="left")
            lbl = tk.Label(fr2, text="—", bg=CARD, fg=ACCENT, font=FONT_VALUE)
            lbl.pack(side="right")
            self._stat_labels[stat] = lbl

    def _run(self):
        try:
            n = int(float(self._n_var.get()))
        except ValueError:
            n = 100000

        result = core.mc_simulate(
            mean_rx_dbm     = self._p_rx.get(),
            sensitivity_dbm = self._sens.get(),
            n_samples       = n,
            model           = self._model.get(),
            K_db            = self._k.get(),
        )
        self._update_stats(result)
        self._plot([result] + self._overlays)

    def _add_overlay(self):
        try:
            n = int(float(self._n_var.get()))
        except ValueError:
            n = 100000
        result = core.mc_simulate(
            mean_rx_dbm     = self._p_rx.get(),
            sensitivity_dbm = self._sens.get(),
            n_samples       = n,
            model           = self._model.get(),
            K_db            = self._k.get(),
        )
        self._overlays.append(result)
        self._run()

    def _clear_overlays(self):
        self._overlays.clear()
        self._run()

    def _update_stats(self, r):
        self._stat_labels["Outage %"].config(
            text=f"{r.outage_prob_pct:.4f}%",
            fg=WARN if r.outage_prob_pct > 5 else ACCENT2)
        self._stat_labels["Mean [dBm]"].config(text=f"{r.mean_rx_dbm:.2f}")
        self._stat_labels["Std [dB]"].config(text=f"{r.std_db:.2f}")
        self._stat_labels["P10 [dBm]"].config(text=f"{r.p10_dbm:.2f}")
        self._stat_labels["P1 [dBm]"].config(text=f"{r.p1_dbm:.2f}")

    def _plot(self, results: list):
        import matplotlib.gridspec as gridspec
        sens  = self._sens.get()

        fig = self._canvas.figure
        fig.clear()
        gs  = gridspec.GridSpec(1, 2, figure=fig, wspace=0.35)
        ax1 = fig.add_subplot(gs[0]); ax1.set_facecolor(PANEL)
        ax2 = fig.add_subplot(gs[1]); ax2.set_facecolor(PANEL)

        primary = results[0]

        for i, r in enumerate(results):
            clr  = COLORS[i % len(COLORS)]
            lbl  = f"{r.model} (K={self._k.get():.0f}dB)" if r.model != "AWGN" else r.model
            bins = np.linspace(primary.samples_dbm.min() - 2,
                               primary.samples_dbm.max() + 2, 120)

            # Histogram (PDF)
            hist, edges = np.histogram(r.samples_dbm, bins=bins, density=True)
            mid = (edges[:-1] + edges[1:]) / 2
            ax1.plot(mid, hist, color=clr, lw=2, label=lbl)

            # CDF
            n    = len(r.samples_dbm)
            srt  = np.sort(r.samples_dbm)
            cdf  = np.arange(1, n + 1) / n * 100
            ax2.semilogy(srt, cdf, color=clr, lw=2, label=lbl)

        # Threshold lines
        ax1.axvline(sens, color=WARN, lw=2, ls="--",
                    label=f"Sens = {sens:.1f} dBm")
        ax1.fill_betweenx([0, ax1.get_ylim()[1] if ax1.get_ylim()[1] > 0 else 0.5],
                           ax1.get_xlim()[0] if ax1.get_xlim() else -150,
                           sens, alpha=0.10, color=WARN)
        ax1.set_xlabel("Received Power [dBm]")
        ax1.set_ylabel("Probability Density")
        ax1.set_title(f"Fading Distribution  (N={len(primary.samples_dbm):,})",
                       color=TEXT)
        ax1.legend(fontsize=8.5, framealpha=0.8)

        ax2.axvline(sens, color=WARN, lw=2, ls="--",
                    label=f"Sens = {sens:.1f} dBm")
        ax2.axhline(primary.outage_prob_pct, color=WARN, lw=1, ls=":")
        ax2.set_xlabel("Received Power [dBm]")
        ax2.set_ylabel("CDF  [%]")
        ax2.set_title(f"CDF  —  Outage = {primary.outage_prob_pct:.3f}%",
                       color=TEXT)
        ax2.set_ylim(0.001, 100)
        ax2.legend(fontsize=8.5, framealpha=0.8)
        ax2.grid(True, which="both", ls="--", alpha=0.3)

        self._canvas.redraw()
