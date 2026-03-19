"""
gui/tabs/cascaded_chain.py
───────────────────────────
Cascaded Noise Figure + IP3 tab.

INTERACTIVE FEATURES:
  • Edit any cell (name / gain / NF / OIP3) → plots update immediately.
  • Add / remove stages dynamically.
  • Hover tooltip shows contribution of each stage to total NF.
  • IIP3, SFDR, and OP1dB computed live.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.gridspec as gridspec

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import core
from core.linearity import spur_free_dynamic_range_db, p1db_from_oip3
from gui.theme   import (BG, CARD, PANEL, BORDER, ACCENT, ACCENT2, WARN,
                          TEXT, TEXT_DIM, FONT_HEAD, FONT_BODY, FONT_RESULT,
                          COLORS)
from gui.widgets import ResultCard, SectionFrame, PlotCanvas, StageRow


class CascadedChainTab(tk.Frame):

    DEBOUNCE_MS = 150

    def __init__(self, parent, defaults: dict, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._stages_data = list(defaults.get("stages", []))
        self._job = None
        self._build()
        self._redraw()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        # Top: stage editor
        editor = tk.Frame(self, bg=BG)
        editor.pack(fill="x", padx=10, pady=(10, 4))
        self._build_editor(editor)

        # Bottom: result cards + plots
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._build_results(bottom)

    def _build_editor(self, parent):
        # Control bar
        ctrl = tk.Frame(parent, bg=CARD, padx=8, pady=6)
        ctrl.pack(fill="x", pady=(0, 4))
        tk.Label(ctrl, text="Receiver Chain Stages",
                 bg=CARD, fg=ACCENT, font=FONT_HEAD).pack(side="left")
        ttk.Button(ctrl, text="+ Add Stage",
                   command=self._add_stage).pack(side="right", padx=4)
        ttk.Button(ctrl, text="− Remove Last",
                   command=self._remove_stage,
                   style="Secondary.TButton").pack(side="right", padx=4)

        # Column headers
        hdr = tk.Frame(parent, bg=PANEL)
        hdr.pack(fill="x")
        for lbl, w in [("#",4),("Name",12),("Gain (dB)",8),
                        ("NF (dB)",8),("OIP3 (dBm)",10)]:
            tk.Label(hdr, text=lbl, bg=PANEL, fg=ACCENT,
                     font=FONT_HEAD, width=w, anchor="center").pack(
                     side="left", padx=4, pady=4)

        # Stage rows container (scrollable region)
        self._rows_frame = tk.Frame(parent, bg=BG)
        self._rows_frame.pack(fill="x")
        self._stage_rows: list[StageRow] = []
        self._rebuild_rows()

    def _rebuild_rows(self):
        for w in self._rows_frame.winfo_children():
            w.destroy()
        self._stage_rows.clear()
        for i, s in enumerate(self._stages_data):
            row = StageRow(self._rows_frame, idx=i+1, defaults=s,
                           on_change=self._schedule, alt=(i % 2 == 1))
            row.pack(fill="x")
            self._stage_rows.append(row)

    def _build_results(self, parent):
        # KPI cards
        cf = tk.Frame(parent, bg=BG)
        cf.pack(fill="x", pady=(0, 6))
        kpis = [("Total Gain","dB"),("Cascaded NF","dB"),
                ("Cascaded OIP3","dBm"),("Cascaded IIP3","dBm"),
                ("SFDR","dB"),("OP1dB","dBm")]
        self._cards: dict[str, ResultCard] = {}
        for i, (n, u) in enumerate(kpis):
            c = ResultCard(cf, n, u)
            c.grid(row=0, column=i, padx=3, sticky="ew")
            cf.columnconfigure(i, weight=1)
            self._cards[n] = c

        # Plot
        self._canvas = PlotCanvas(parent, figsize=(9.5, 4.2))
        self._canvas.pack(fill="both", expand=True)

    # ── Stage management ─────────────────────────────────────────────────────

    def _add_stage(self):
        self._stages_data.append({"name": f"Stage{len(self._stages_data)+1}",
                                   "gain_db": 10.0, "nf_db": 5.0, "oip3_dbm": 25.0})
        self._rebuild_rows()
        self._schedule()

    def _remove_stage(self):
        if len(self._stages_data) > 1:
            self._stages_data.pop()
            self._rebuild_rows()
            self._schedule()

    # ── Debounced redraw ─────────────────────────────────────────────────────

    def _schedule(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self.DEBOUNCE_MS, self._redraw)

    # ── Core redraw ──────────────────────────────────────────────────────────

    def _read_stages(self):
        stages = []
        for row in self._stage_rows:
            data = row.get()
            if data is None:
                return None
            stages.append(data)
        return stages

    def _redraw(self):
        stages = self._read_stages()
        if not stages:
            return

        names  = [s["name"]     for s in stages]
        gains  = [s["gain_db"]  for s in stages]
        nfs    = [s["nf_db"]    for s in stages]
        oip3s  = [s["oip3_dbm"] for s in stages]

        # ── Computations ──
        total_gain  = sum(gains)
        cas_nf      = core.cascaded_nf_db(nfs, gains)
        cas_oip3    = core.cascaded_oip3_dbm(oip3s, gains)
        cas_iip3    = core.iip3_from_oip3_dbm(cas_oip3, total_gain)
        noise_floor = core.thermal_noise_dbm(20e6)   # 20 MHz reference
        sfdr        = spur_free_dynamic_range_db(cas_oip3, noise_floor)
        op1db       = p1db_from_oip3(cas_oip3)

        cum_nf_list  = core.cumulative_nf_db(nfs, gains)
        cum_gain_list = core.cumulative_gain_db(gains)

        # ── KPI cards ──
        self._cards["Total Gain"].update(total_gain)
        self._cards["Cascaded NF"].update(cas_nf,
            good=(cas_nf < 5))
        self._cards["Cascaded OIP3"].update(cas_oip3)
        self._cards["Cascaded IIP3"].update(cas_iip3)
        self._cards["SFDR"].update(sfdr)
        self._cards["OP1dB"].update(op1db)

        # ── Plots ──
        fig = self._canvas.figure
        fig.clear()
        gs  = gridspec.GridSpec(1, 3, figure=fig, wspace=0.4)
        ax1 = fig.add_subplot(gs[0]); ax1.set_facecolor(PANEL)
        ax2 = fig.add_subplot(gs[1]); ax2.set_facecolor(PANEL)
        ax3 = fig.add_subplot(gs[2]); ax3.set_facecolor(PANEL)
        x   = np.arange(len(names))

        # NF build-up
        ax1.bar(x, cum_nf_list, color=ACCENT, alpha=0.55, zorder=3)
        ax1.plot(x, cum_nf_list, "o-", color=WARN, lw=2, ms=7, zorder=4)
        ax1.axhline(cas_nf, color=ACCENT2, ls="--", lw=1.8,
                    label=f"Total NF = {cas_nf:.2f} dB")
        for xi, v in zip(x, cum_nf_list):
            ax1.text(xi, v + 0.1, f"{v:.2f}", ha="center",
                      fontsize=7.5, color=TEXT)
        ax1.set_xticks(x); ax1.set_xticklabels(names, rotation=28, ha="right", fontsize=8)
        ax1.set_ylabel("Cumulative NF [dB]")
        ax1.set_title("NF Build-up (Friis)", color=TEXT)
        ax1.legend(fontsize=8)

        # Per-stage NF contribution bar
        nf_contrib = [cum_nf_list[0]] + [cum_nf_list[i] - cum_nf_list[i-1]
                                          for i in range(1, len(cum_nf_list))]
        ax2.bar(x, nf_contrib, color=[WARN if v == max(nf_contrib)
                                       else ACCENT for v in nf_contrib],
                alpha=0.75, zorder=3)
        ax2.set_xticks(x); ax2.set_xticklabels(names, rotation=28, ha="right", fontsize=8)
        ax2.set_ylabel("NF Contribution [dB]")
        ax2.set_title("Per-Stage NF Contribution", color=TEXT)
        worst = names[np.argmax(nf_contrib)]
        ax2.text(0.98, 0.95, f"Bottleneck: {worst}", transform=ax2.transAxes,
                  ha="right", va="top", fontsize=8, color=WARN)

        # Cumulative gain
        ax3.bar(x, cum_gain_list,
                color=[ACCENT2 if v >= 0 else WARN for v in cum_gain_list],
                alpha=0.7, zorder=3)
        ax3.plot(x, cum_gain_list, "s-", color=ACCENT, lw=2, ms=6, zorder=4)
        ax3.axhline(0, color=BORDER, lw=1)
        for xi, v in zip(x, cum_gain_list):
            ax3.text(xi, v + (0.3 if v >= 0 else -0.8), f"{v:.1f}",
                      ha="center", fontsize=7.5, color=TEXT)
        ax3.set_xticks(x); ax3.set_xticklabels(names, rotation=28, ha="right", fontsize=8)
        ax3.set_ylabel("Cumulative Gain [dB]")
        ax3.set_title(f"Signal Gain  (Total: {total_gain:.1f} dB)", color=TEXT)

        self._canvas.redraw()
