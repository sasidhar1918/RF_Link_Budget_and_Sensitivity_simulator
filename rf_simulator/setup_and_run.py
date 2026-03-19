#!/usr/bin/env python3
"""
setup_and_run.py
─────────────────
One-click setup + launch for RF Link Budget Simulator.

Usage:
    python setup_and_run.py          # install deps + launch GUI
    python setup_and_run.py --check  # only check/install, don't launch
    python setup_and_run.py --test   # install + run unit tests
"""

import sys
import os
import subprocess
import importlib
import argparse
import platform

# ── Minimum Python version ───────────────────────────────────────────────────
MIN_PYTHON = (3, 10)

# ── Required pip packages: (import_name, pip_name, min_version) ──────────────
REQUIRED = [
    ("numpy",      "numpy",      "1.24"),
    ("scipy",      "scipy",      "1.10"),
    ("matplotlib", "matplotlib", "3.7"),
]

# ── Colour helpers (work without any external package) ───────────────────────
def _c(code, text): return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text
ok   = lambda t: print(_c("32", f"  ✔  {t}"))
warn = lambda t: print(_c("33", f"  ⚠  {t}"))
err  = lambda t: print(_c("31", f"  ✘  {t}"))
info = lambda t: print(_c("36", f"  →  {t}"))
head = lambda t: print(_c("1;34", f"\n{'─'*54}\n  {t}\n{'─'*54}"))


# ── Version comparison ────────────────────────────────────────────────────────
def _ver(s):
    return tuple(int(x) for x in str(s).split(".")[:3])


# ── Check + install one package ───────────────────────────────────────────────
def ensure(import_name, pip_name, min_ver):
    try:
        mod = importlib.import_module(import_name)
        installed = getattr(mod, "__version__", "0")
        if _ver(installed) >= _ver(min_ver):
            ok(f"{pip_name} {installed}")
            return True
        warn(f"{pip_name} {installed} is below minimum {min_ver} — upgrading …")
    except ImportError:
        warn(f"{pip_name} not found — installing …")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install",
         f"{pip_name}>={min_ver}", "--upgrade", "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err(f"Failed to install {pip_name}:\n{result.stderr.strip()}")
        return False

    # Reload after install
    try:
        if import_name in sys.modules:
            del sys.modules[import_name]
        mod = importlib.import_module(import_name)
        ok(f"{pip_name} {getattr(mod, '__version__', '?')}  (just installed)")
        return True
    except ImportError:
        err(f"Installed {pip_name} but still cannot import it.")
        return False


# ── tkinter check (stdlib, not pip-installable) ───────────────────────────────
def check_tkinter():
    try:
        import tkinter  # noqa: F401
        ok("tkinter (stdlib)")
        return True
    except ImportError:
        system = platform.system()
        err("tkinter not found — it is part of Python's standard library")
        err("but must be installed separately on some systems:")
        if system == "Linux":
            distro = ""
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("ID="):
                            distro = line.split("=")[1].strip().strip('"').lower()
            except Exception:
                pass
            if distro in ("ubuntu", "debian", "linuxmint", "pop"):
                info("Run:  sudo apt install python3-tk")
            elif distro in ("fedora", "rhel", "centos", "rocky"):
                info("Run:  sudo dnf install python3-tkinter")
            elif distro in ("arch", "manjaro"):
                info("Run:  sudo pacman -S tk")
            else:
                info("Run:  sudo apt install python3-tk   (Debian/Ubuntu)")
                info("  or: sudo dnf install python3-tkinter  (Fedora/RHEL)")
        elif system == "Darwin":
            info("If using pyenv/Homebrew Python:")
            info("  brew install python-tk")
            info("  or reinstall Python via: pyenv install 3.x.x")
            info("Official python.org installer includes tkinter by default.")
        elif system == "Windows":
            info("Re-run the Python installer from python.org")
            info("and tick 'tcl/tk and IDLE' in Optional Features.")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Setup and run RF Simulator")
    parser.add_argument("--check", action="store_true",
                        help="Only check/install dependencies, do not launch GUI")
    parser.add_argument("--test",  action="store_true",
                        help="Install deps then run unit tests")
    args = parser.parse_args()

    head("Python version check")
    pv = sys.version_info[:2]
    if pv >= MIN_PYTHON:
        ok(f"Python {sys.version.split()[0]}  (>= {'.'.join(map(str, MIN_PYTHON))} required)")
    else:
        err(f"Python {'.'.join(map(str, pv))} is too old.")
        err(f"Please install Python {'.'.join(map(str, MIN_PYTHON))} or newer.")
        err("Download from: https://www.python.org/downloads/")
        sys.exit(1)

    head("Checking pip packages")
    all_ok = all(ensure(i, p, v) for i, p, v in REQUIRED)

    head("Checking tkinter")
    tk_ok = check_tkinter()

    if not all_ok or not tk_ok:
        print()
        err("One or more dependencies are missing. Fix the errors above, then re-run.")
        sys.exit(1)

    if args.test:
        head("Running unit tests")
        # Install pytest if needed
        ensure("pytest", "pytest", "7.0")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        sys.exit(result.returncode)

    if args.check:
        head("All dependencies satisfied")
        ok("Ready to run:  python main.py")
        sys.exit(0)

    head("Launching RF Simulator …")
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    # Import and launch directly in same process (no subprocess overhead)
    sys.path.insert(0, root)
    try:
        from gui.app import RFSimulatorApp
        import matplotlib
        from gui.theme import MPL_STYLE
        matplotlib.rcParams.update(MPL_STYLE)
        app = RFSimulatorApp()
        app.mainloop()
    except Exception as exc:
        err(f"Failed to launch: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
