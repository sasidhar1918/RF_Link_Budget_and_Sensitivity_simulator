"""
gui/app.py
───────────
RFSimulatorApp — top-level Tk window.

Responsibilities (and ONLY these):
  1. Create the window and apply the theme.
  2. Load defaults from config/defaults.json.
  3. Instantiate each tab and register it with the Notebook.
  4. Provide a global status bar.

All domain logic lives in core/.
All widget logic lives in gui/tabs/.
"""

import tkinter as tk
from tkinter import ttk
import json, os, sys

# Ensure project root is on path when running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gui.theme import apply_ttk_theme, BG, PANEL, ACCENT, TEXT_DIM, FONT_TITLE, FONT_SMALL, MPL_STYLE
import matplotlib; matplotlib.rcParams.update(MPL_STYLE)

from gui.tabs.link_budget    import LinkBudgetTab
from gui.tabs.cascaded_chain import CascadedChainTab
from gui.tabs.path_loss      import PathLossTab
from gui.tabs.ber_plots      import BERPlotsTab
from gui.tabs.sensitivity    import SensitivityTab
from gui.tabs.monte_carlo    import MonteCarloTab


_DEFAULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "defaults.json")


class RFSimulatorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("RF Link Budget + Sensitivity Simulator  v2.0  (Modular)")
        self.geometry("1450x940")
        self.configure(bg=BG)
        self.resizable(True, True)

        apply_ttk_theme(self)
        self._defaults = self._load_defaults()
        self._build()

    def _load_defaults(self) -> dict:
        try:
            with open(_DEFAULTS_PATH) as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[WARN] defaults.json not found at {_DEFAULTS_PATH} — tabs will use hardcoded fallbacks.")
            return {}
        except Exception as exc:
            print(f"[ERROR] Could not parse defaults.json: {exc} — tabs will use hardcoded fallbacks.")
            return {}

    def _build(self):
        self._build_header()
        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")
        self._build_notebook()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=PANEL, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr,
                 text="⚡  RF LINK BUDGET + SENSITIVITY SIMULATOR",
                 bg=PANEL, fg=ACCENT, font=FONT_TITLE).pack(side="left", padx=18, pady=8)
        tk.Label(hdr,
                 text="v2.0  |  Modular  |  Live Sliders  |  Real-Time Plots",
                 bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).pack(side="right", padx=18)

    def _build_notebook(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        tabs = [
            ("  📡 Link Budget  ",    LinkBudgetTab,    self._defaults.get("link_budget", {})),
            ("  🔗 Cascaded Chain  ", CascadedChainTab, self._defaults.get("chain", {})),
            ("  📶 Path Loss  ",      PathLossTab,      self._defaults.get("path_loss", {})),
            ("  📊 BER vs SNR  ",     BERPlotsTab,      self._defaults.get("ber", {})),
            ("  📉 Sensitivity  ",    SensitivityTab,   self._defaults.get("sensitivity", {})),
            ("  🎲 Monte Carlo  ",    MonteCarloTab,    self._defaults.get("monte_carlo", {})),
        ]
        for title, TabClass, defaults in tabs:
            frame = TabClass(self.nb, defaults=defaults)
            self.nb.add(frame, text=title)

    def _build_statusbar(self):
        sb = tk.Frame(self, bg=PANEL, height=24)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        tk.Label(sb,
                 text="  All plots update in real time as you move sliders  •  "
                      "📌 Save Overlay = compare before/after  •  "
                      "Operating point markers show live values",
                 bg=PANEL, fg=TEXT_DIM, font=FONT_SMALL).pack(side="left", padx=10)
