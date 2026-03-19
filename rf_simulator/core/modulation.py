"""
core/modulation.py
──────────────────
Analytical BER vs Es/N0 for standard digital modulations.
Pure math — zero GUI dependency.
"""

import numpy as np
from scipy import special


def _qfunc(x):
    """Q-function  Q(x) = 0.5·erfc(x/√2)."""
    return 0.5 * special.erfc(np.asarray(x) / np.sqrt(2))


# ── Per-modulation BER expressions ──────────────────────────────────────────

def ber_bpsk(snr_lin):
    return _qfunc(np.sqrt(2 * snr_lin))


def ber_qpsk(snr_lin):
    """QPSK BER = BPSK BER (same Es/N0 performance)."""
    return _qfunc(np.sqrt(2 * snr_lin))


def ber_8psk(snr_lin):
    return (2 / 3) * _qfunc(np.sqrt(2 * snr_lin) * np.sin(np.pi / 8))


def ber_16qam(snr_lin):
    return (3 / 4) * _qfunc(np.sqrt(snr_lin * 4 / 5))


def ber_64qam(snr_lin):
    return (7 / 12) * _qfunc(np.sqrt(snr_lin * 2 / 7))


def ber_256qam(snr_lin):
    return (15 / 32) * _qfunc(np.sqrt(snr_lin * 2 / 85))


# ── Dispatch table ───────────────────────────────────────────────────────────

MODULATIONS = {
    "BPSK":   ber_bpsk,
    "QPSK":   ber_qpsk,
    "8PSK":   ber_8psk,
    "16QAM":  ber_16qam,
    "64QAM":  ber_64qam,
    "256QAM": ber_256qam,
}

SPECTRAL_EFFICIENCY = {
    "BPSK":   1,
    "QPSK":   2,
    "8PSK":   3,
    "16QAM":  4,
    "64QAM":  6,
    "256QAM": 8,
}


def ber_vs_snr(snr_lin, modulation: str = "BPSK") -> np.ndarray:
    """
    BER for the given modulation over an array of Es/N0 values (linear).
    Returns array of same shape as snr_lin.
    """
    fn = MODULATIONS.get(modulation)
    if fn is None:
        raise ValueError(f"Unknown modulation '{modulation}'. "
                         f"Choose from: {list(MODULATIONS)}")
    return np.maximum(fn(np.asarray(snr_lin, dtype=float)), 1e-15)


def snr_for_ber_target(ber_target: float, modulation: str = "BPSK") -> float:
    """
    SNR [dB] required to achieve ber_target.
    Solved by scanning a fine grid (accurate to ~0.01 dB).
    """
    snr_db  = np.linspace(0, 40, 8000)
    snr_lin = 10 ** (snr_db / 10)
    ber     = ber_vs_snr(snr_lin, modulation)
    idx     = np.where(ber <= ber_target)[0]
    return float(snr_db[idx[0]]) if len(idx) > 0 else 40.0
