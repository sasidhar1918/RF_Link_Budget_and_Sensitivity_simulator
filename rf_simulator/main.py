"""
main.py
────────
Entry point — 10 lines, no logic.

Run:
    python main.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from gui.app import RFSimulatorApp

if __name__ == "__main__":
    app = RFSimulatorApp()
    app.mainloop()
