"""
core/friis.py
─────────────
Friis transmission equation and free-space path loss.
Pure math — zero GUI dependency, fully unit-testable.
"""

import numpy as np

C = 3e8   # speed of light [m/s]


def free_space_path_loss_db(freq_hz: float, distance_m: float) -> float:
    """
    Free-Space Path Loss (FSPL) via Friis [dB].
      FSPL = 20·log10(4π·d·f / c)

    Note: distance_m = 0 returns -300 dB (log guard) rather than raising.
    Callers should ensure distance_m > 0 for physically meaningful results.
    """
    lam  = C / np.asarray(freq_hz, dtype=float)
    fspl = (4 * np.pi * np.asarray(distance_m, dtype=float) / lam) ** 2
    return 10 * np.log10(np.maximum(fspl, 1e-30))


def received_power_dbm(
    p_tx_dbm:   float,
    g_tx_dbi:   float,
    g_rx_dbi:   float,
    freq_hz:    float,
    distance_m: float,
    loss_tx_db: float = 0.0,
    loss_rx_db: float = 0.0,
    misc_loss_db: float = 0.0,
) -> float:
    """
    Friis received power [dBm].
      P_rx = P_tx + G_tx - L_tx - FSPL - misc + G_rx - L_rx
    """
    fspl = free_space_path_loss_db(freq_hz, distance_m)
    return (p_tx_dbm + g_tx_dbi + g_rx_dbi
            - fspl - loss_tx_db - loss_rx_db - misc_loss_db)


def eirp_dbm(p_tx_dbm: float, g_tx_dbi: float, loss_tx_db: float = 0.0) -> float:
    """Effective Isotropic Radiated Power [dBm]."""
    return p_tx_dbm + g_tx_dbi - loss_tx_db


def max_range_m(
    p_tx_dbm: float,
    g_tx_dbi: float,
    g_rx_dbi: float,
    freq_hz:  float,
    sensitivity_dbm: float,
    loss_tx_db: float = 0.0,
    loss_rx_db: float = 0.0,
) -> float:
    """
    Maximum communication range [m] given a sensitivity floor.
    Solved analytically from Friis:
      d_max = (λ/4π) · 10^((EIRP + G_rx - L_rx - S) / 20)
    """
    lam   = C / freq_hz
    budget = (p_tx_dbm + g_tx_dbi - loss_tx_db
              + g_rx_dbi - loss_rx_db - sensitivity_dbm)
    return (lam / (4 * np.pi)) * 10 ** (budget / 20)
