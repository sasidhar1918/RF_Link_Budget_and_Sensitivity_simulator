"""
core/path_loss.py
──────────────────
Path loss propagation models.
  • Free Space (Friis)
  • Okumura-Hata  (150–1500 MHz)
  • COST-231 Hata (1500–2000 MHz)

All functions accept numpy arrays for vectorised distance sweeps.
Pure math — zero GUI dependency.
"""

import numpy as np
from core.friis import free_space_path_loss_db


# ── Free Space ──────────────────────────────────────────────────────────────

def free_space(freq_hz: float, distance_m) -> np.ndarray:
    """FSPL [dB]. Thin wrapper kept for uniform API."""
    return free_space_path_loss_db(freq_hz, distance_m)


# ── Okumura-Hata ─────────────────────────────────────────────────────────────

def _hata_mobile_correction(freq_mhz: float, h_ms_m: float,
                              env: str) -> float:
    """a(h_ms) correction factor for Okumura-Hata."""
    f = freq_mhz
    h = h_ms_m
    if env == "urban_large":
        if f >= 300:
            return (3.2 * (np.log10(11.75 * h)) ** 2 - 4.97)
        else:
            return (8.29 * (np.log10(1.54 * h)) ** 2 - 1.1)
    else:   # small/medium city (default)
        return (1.1 * np.log10(f) - 0.7) * h - (1.56 * np.log10(f) - 0.8)


def okumura_hata(
    freq_mhz: float,
    distance_km,
    h_bs_m:   float = 30.0,
    h_ms_m:   float = 1.5,
    env:      str   = "urban",
) -> np.ndarray:
    """
    Okumura-Hata path loss [dB].
    Valid range: 150-1500 MHz, 1-20 km.

    env options: 'urban', 'suburban', 'open', 'urban_large'
    """
    f  = float(np.clip(freq_mhz, 150, 1500))
    d  = np.maximum(np.asarray(distance_km, dtype=float), 0.01)
    hb = float(h_bs_m)

    a_hm = _hata_mobile_correction(f, h_ms_m,
                                    "urban_large" if env == "urban_large" else "small")

    L_u = (69.55
           + 26.16 * np.log10(f)
           - 13.82 * np.log10(hb)
           - a_hm
           + (44.9 - 6.55 * np.log10(hb)) * np.log10(d))

    if env in ("urban", "urban_large"):
        return L_u
    elif env == "suburban":
        Q = np.log10(f / 28)
        return L_u - 2 * Q ** 2 - 5.4
    else:   # open
        return (L_u
                - 4.78 * np.log10(f) ** 2
                + 18.33 * np.log10(f)
                - 40.94)


# ── COST-231 Hata ─────────────────────────────────────────────────────────────

def cost231_hata(
    freq_mhz: float,
    distance_km,
    h_bs_m:   float = 30.0,
    h_ms_m:   float = 1.5,
    city:     str   = "medium",
) -> np.ndarray:
    """
    COST-231 Hata model [dB].
    Valid range: 1500-2000 MHz.

    city options: 'medium' (C=0), 'large' (C=3)
    """
    f  = float(np.clip(freq_mhz, 1500, 2000))
    d  = np.maximum(np.asarray(distance_km, dtype=float), 0.01)
    hb = float(h_bs_m)
    C  = 3.0 if city == "large" else 0.0

    a_hm = ((1.1 * np.log10(f) - 0.7) * h_ms_m
             - (1.56 * np.log10(f) - 0.8))

    return (46.3
            + 33.9 * np.log10(f)
            - 13.82 * np.log10(hb)
            - a_hm
            + (44.9 - 6.55 * np.log10(hb)) * np.log10(d)
            + C)


# ── Model registry — for dynamic tab population ──────────────────────────────

MODEL_REGISTRY = {
    "Free Space": {
        "fn":    lambda p, d: free_space(p["freq_hz"], d * 1e3),
        "valid": (0, 1e6),
        "color_key": 0,
    },
    "Okumura-Hata Urban": {
        "fn":    lambda p, d: okumura_hata(p["freq_mhz"], d, p["h_bs"], p["h_ms"], "urban"),
        "valid": (150, 1500),
        "color_key": 1,
    },
    "Okumura-Hata Suburban": {
        "fn":    lambda p, d: okumura_hata(p["freq_mhz"], d, p["h_bs"], p["h_ms"], "suburban"),
        "valid": (150, 1500),
        "color_key": 2,
    },
    "Okumura-Hata Open": {
        "fn":    lambda p, d: okumura_hata(p["freq_mhz"], d, p["h_bs"], p["h_ms"], "open"),
        "valid": (150, 1500),
        "color_key": 3,
    },
    "COST-231 Medium City": {
        "fn":    lambda p, d: cost231_hata(p["freq_mhz"], d, p["h_bs"], p["h_ms"], "medium"),
        "valid": (1500, 2000),
        "color_key": 4,
    },
    "COST-231 Large City": {
        "fn":    lambda p, d: cost231_hata(p["freq_mhz"], d, p["h_bs"], p["h_ms"], "large"),
        "valid": (1500, 2000),
        "color_key": 5,
    },
}
