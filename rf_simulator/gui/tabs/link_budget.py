"""
gui/tabs/link_budget.py
────────────────────────
Link Budget tab.

KEY INTERACTIVE FEATURES:
  • Every parameter has a slider — move it and the plot + result cards
    update in real time (debounced to 120 ms so it's smooth, not laggy).
  • Distance sweep plot shows the operating point as a live marker.
  • Fade margin indicator changes colour: green ≥10 dB, yellow 0–10, red <0.
  • "Compare" button overlays the current curve against previous settings.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.gridspec as gridspec

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import core
from gui.theme   import (BG, CARD, PANEL, BORDER, ACCENT, ACCENT2, WARN,
                          TEXT, TEXT_DIM, FONT_HEAD, FONT_BODY, FONT_SMALL,
                          FONT_RESULT, COLORS)
from gui.widgets import LiveSlider, ResultCard, SectionFrame, PlotCanvas


class LinkBudgetTab(tk.Frame):

    DEBOUNCE_MS = 120   # ms to wait after last slider move before redraw

    def __init__(self, parent, defaults: dict, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._d       = defaults
        self._job     = None          # pending after() id
        self._overlays: list = []     # list of saved (p_rx array, label) tuples

        self._build()
        self._redraw()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        # Split: left panel (controls) | right panel (plots + cards)
        self._left = tk.Frame(self, bg=BG, width=310)
        self._left.pack(side="left", fill="y", padx=(10, 6), pady=10)
        self._left.pack_propagate(False)

        self._right = tk.Frame(self, bg=BG)
        self._right.pack(side="left", fill="both", expand=True,
                          padx=(0, 10), pady=10)

        self._build_controls()
        self._build_results()

    def _build_controls(self):
        d = self._d

        def slider(parent, lbl, lo, hi, default, unit, res=0.5):
            s = LiveSlider(parent, lbl, lo, hi, default, unit,
                           resolution=res, on_change=self._schedule)
            s.pack(fill="x", pady=2, padx=4)
            return s

        # ── TX ──
        tx = SectionFrame(self._left, "Transmitter")
        tx.pack(fill="x", pady=(0, 6))
        self._p_tx    = slider(tx, "TX Power",         0,   50,  d.get("p_tx_dbm", 30),   "dBm")
        self._g_tx    = slider(tx, "TX Antenna Gain",  0,   40,  d.get("g_tx_dbi", 15),   "dBi")
        self._loss_tx = slider(tx, "TX Feed Loss",     0,   10,  d.get("loss_tx_db", 1.5), "dB", 0.1)

        # ── Channel ──
        ch = SectionFrame(self._left, "Channel")
        ch.pack(fill="x", pady=(0, 6))
        self._freq     = slider(ch, "Frequency",       100, 6000, d.get("freq_mhz", 2400),   "MHz", 10)
        self._dist     = slider(ch, "Distance",        0.1,  100, d.get("dist_km", 5),    "km",  0.1)
        self._misc     = slider(ch, "Misc. Loss",      0,    20,  d.get("misc_loss_db", 2),"dB", 0.5)

        # ── RX ──
        rx = SectionFrame(self._left, "Receiver")
        rx.pack(fill="x", pady=(0, 6))
        self._g_rx     = slider(rx, "RX Antenna Gain", 0,   40, d.get("g_rx_dbi", 5),    "dBi")
        self._loss_rx  = slider(rx, "RX Feed Loss",    0,   10, d.get("loss_rx_db", 0.5),  "dB", 0.1)
        self._nf       = slider(rx, "Noise Figure",    0,   20, d.get("nf_db", 5),       "dB", 0.1)
        self._bw       = slider(rx, "Bandwidth",       0.1, 500, d.get("bw_mhz", 20),     "MHz", 1)
        self._snr_req  = slider(rx, "Required SNR",    0,   30, d.get("snr_req_db", 10),  "dB", 0.5)

        # ── Overlay button ──
        bf = tk.Frame(self._left, bg=BG)
        bf.pack(fill="x", pady=6)
        ttk.Button(bf, text="📌 Save Overlay",
                   command=self._save_overlay,
                   style="Secondary.TButton").pack(side="left", padx=4)
        ttk.Button(bf, text="✕ Clear Overlays",
                   command=self._clear_overlays,
                   style="Secondary.TButton").pack(side="left", padx=4)

    def _build_results(self):
        # ── KPI cards row ──
        cards_frame = tk.Frame(self._right, bg=BG)
        cards_frame.pack(fill="x", pady=(0, 6))

        kpis = [
            ("P_RX",        "dBm"),
            ("Sensitivity", "dBm"),
            ("Fade Margin", "dB"),
            ("EIRP",        "dBm"),
            ("FSPL",        "dB"),
            ("Max Range",   "km"),
        ]
        self._cards: dict[str, ResultCard] = {}
        for i, (name, unit) in enumerate(kpis):
            c = ResultCard(cards_frame, name, unit)
            c.grid(row=0, column=i, padx=4, sticky="ew")
            cards_frame.columnconfigure(i, weight=1)
            self._cards[name] = c

        # ── Plot canvas ──
        self._canvas = PlotCanvas(self._right, figsize=(9.5, 5.0))
        self._canvas.pack(fill="both", expand=True)

    # ── Debounced redraw ─────────────────────────────────────────────────────

    def _schedule(self, _=None):
        """Called on every slider tick — debounced."""
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self.DEBOUNCE_MS, self._redraw)

    # ── Core redraw ──────────────────────────────────────────────────────────

    def _read_params(self):
        return dict(
            p_tx    = self._p_tx.get(),
            g_tx    = self._g_tx.get(),
            l_tx    = self._loss_tx.get(),
            freq_hz = self._freq.get() * 1e6,
            dist_m  = self._dist.get() * 1e3,
            misc    = self._misc.get(),
            g_rx    = self._g_rx.get(),
            l_rx    = self._loss_rx.get(),
            nf      = self._nf.get(),
            bw_hz   = self._bw.get() * 1e6,
            snr_req = self._snr_req.get(),
        )

    def _redraw(self):
        p = self._read_params()

        # ── Core calculations ──
        fspl     = core.free_space_path_loss_db(p["freq_hz"], p["dist_m"])
        p_rx     = core.received_power_dbm(
                       p["p_tx"], p["g_tx"], p["g_rx"],
                       p["freq_hz"], p["dist_m"],
                       p["l_tx"], p["l_rx"], p["misc"])
        eirp     = core.eirp_dbm(p["p_tx"], p["g_tx"], p["l_tx"])
        sens     = core.receiver_sensitivity_dbm(p["bw_hz"], p["nf"], p["snr_req"])
        fm       = p_rx - sens
        max_r    = core.max_range_m(p["p_tx"], p["g_tx"], p["g_rx"],
                                     p["freq_hz"], sens, p["l_tx"], p["l_rx"]) / 1e3

        # ── Update KPI cards ──
        self._cards["P_RX"].update(p_rx)
        self._cards["Sensitivity"].update(sens)
        self._cards["Fade Margin"].update(
            fm,
            status="✅ >10 dB" if fm >= 10 else ("⚠ marginal" if fm >= 0 else "❌ outage"),
            good=True if fm >= 10 else (None if fm >= 0 else False))
        # good=True  → green  (fm ≥ 10 dB, comfortable margin)
        # good=None  → grey   (0–10 dB, marginal — link works but no headroom)
        # good=False → red    (fm < 0,   outage — link fails)
        self._cards["EIRP"].update(eirp)
        self._cards["FSPL"].update(fspl)
        self._cards["Max Range"].update(max_r,
            status=f"@ {p['freq_hz']/1e9:.2f} GHz",
            good=max_r > self._dist.get())

        # ── Plot ──
        fig  = self._canvas.figure
        fig.clear()
        gs   = gridspec.GridSpec(1, 2, figure=fig, wspace=0.35)
        ax1  = fig.add_subplot(gs[0]); ax1.set_facecolor(PANEL)
        ax2  = fig.add_subplot(gs[1]); ax2.set_facecolor(PANEL)

        # Distance sweep
        d_km = np.logspace(-2, np.log10(max(max_r * 2, 1)), 400)
        d_m  = d_km * 1e3
        p_rx_sweep = core.received_power_dbm(
                         p["p_tx"], p["g_tx"], p["g_rx"],
                         p["freq_hz"], d_m,
                         p["l_tx"], p["l_rx"], p["misc"])

        # Overlays
        for ox, olbl in self._overlays:
            ax1.semilogx(ox[0], ox[1], color=TEXT_DIM, lw=1.2,
                          ls="--", alpha=0.55, label=olbl)

        ax1.semilogx(d_km, p_rx_sweep, color=ACCENT, lw=2.2, label="P_rx (current)")
        ax1.axhline(sens, color=WARN, lw=2, ls="--",
                    label=f"Sensitivity = {sens:.1f} dBm")
        ax1.axvline(self._dist.get(), color=ACCENT2, lw=1.5, ls=":",
                    label=f"d = {self._dist.get():.1f} km")

        # Operating point marker
        ax1.plot(self._dist.get(), p_rx, "o", color=ACCENT2,
                  ms=9, zorder=5,
                  label=f"P_rx = {p_rx:.1f} dBm")

        ax1.fill_between(d_km, p_rx_sweep, sens,
                          where=p_rx_sweep >= sens, alpha=0.10, color=ACCENT2)
        ax1.fill_between(d_km, p_rx_sweep, sens,
                          where=p_rx_sweep < sens,  alpha=0.10, color=WARN)

        ax1.set_xlabel("Distance [km]")
        ax1.set_ylabel("Received Power [dBm]")
        ax1.set_title("Rx Power vs Distance  (live)", color=TEXT)
        ax1.legend(fontsize=8, framealpha=0.8)

        # Fade margin waterfall (bar chart)
        items  = ["P_TX", "+G_TX", "−L_TX", "−FSPL",
                  "−Misc", "+G_RX", "−L_RX"]
        deltas = [p["p_tx"], p["g_tx"], -p["l_tx"],
                  -fspl, -p["misc"], p["g_rx"], -p["l_rx"]]
        running = 0.0
        bars_x, bars_w, bars_c = [], [], []
        for delta in deltas:
            bars_x.append(running)
            bars_w.append(delta)
            bars_c.append(ACCENT2 if delta >= 0 else WARN)
            running += delta

        ax2.barh(range(len(items)), bars_w, left=bars_x,
                  color=bars_c, alpha=0.75, height=0.55, zorder=3)
        ax2.axvline(sens, color=WARN, lw=2, ls="--",
                    label=f"Sens={sens:.1f}dBm")
        ax2.axvline(p_rx, color=ACCENT2, lw=2, ls="-.",
                    label=f"P_rx={p_rx:.1f}dBm")

        # Annotate each bar with its cumulative value
        cum = 0.0
        for i, (dx, item) in enumerate(zip(deltas, items)):
            cum += dx
            ax2.text(cum + (0.4 if dx >= 0 else -0.4), i,
                      f"{cum:.1f}", va="center",
                      ha="left" if dx >= 0 else "right",
                      fontsize=7.5, color=TEXT)

        ax2.set_yticks(range(len(items)))
        ax2.set_yticklabels(items, fontsize=9)
        ax2.set_xlabel("Power [dBm]")
        ax2.set_title(f"Budget Waterfall  |  FM = {fm:.1f} dB", color=TEXT)
        ax2.legend(fontsize=8, framealpha=0.8)

        self._canvas.redraw()

    # ── Overlay helpers ──────────────────────────────────────────────────────

    def _save_overlay(self):
        p    = self._read_params()
        d_km = np.logspace(-2, 3, 400)
        d_m  = d_km * 1e3
        p_sweep = core.received_power_dbm(
                      p["p_tx"], p["g_tx"], p["g_rx"],
                      p["freq_hz"], d_m,
                      p["l_tx"], p["l_rx"], p["misc"])
        lbl = (f"{self._freq.get():.0f}MHz "
               f"P={self._p_tx.get():.0f}dBm")
        self._overlays.append(((d_km, p_sweep), lbl))
        self._redraw()

    def _clear_overlays(self):
        self._overlays.clear()
        self._redraw()
