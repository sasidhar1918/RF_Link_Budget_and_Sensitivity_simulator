"""
core/noise.py
─────────────
Thermal noise, cascaded noise figure (Friis formula), receiver sensitivity.
Pure math — zero GUI dependency.
"""

import numpy as np

K_B   = 1.380649e-23   # Boltzmann constant [J/K]
T_STD = 290.0          # Standard temperature [K]


def thermal_noise_dbm(bw_hz: float, temp_k: float = T_STD) -> float:
    """
    Thermal noise power = k·T·B  [dBm].
    """
    noise_w = K_B * np.asarray(temp_k) * np.asarray(bw_hz)
    return 10 * np.log10(np.maximum(noise_w, 1e-30) / 1e-3)


def noise_figure_to_temp(nf_db: float, t_ref: float = T_STD) -> float:
    """Convert NF [dB] to equivalent noise temperature [K]."""
    F = 10 ** (nf_db / 10)
    return t_ref * (F - 1)


def cascaded_nf_db(nf_list_db: list, gain_list_db: list) -> float:
    """
    Friis cascaded noise figure for N stages [dB].
      F_total = F1 + (F2-1)/G1 + (F3-1)/(G1·G2) + ...
    """
    if len(nf_list_db) != len(gain_list_db):
        raise ValueError("nf_list and gain_list must have the same length.")
    nf_lin   = [10 ** (n / 10) for n in nf_list_db]
    gain_lin = [10 ** (g / 10) for g in gain_list_db]
    F_total  = nf_lin[0]
    cum_gain = gain_lin[0]
    for i in range(1, len(nf_lin)):
        F_total  += (nf_lin[i] - 1) / cum_gain
        cum_gain *= gain_lin[i]
    return 10 * np.log10(F_total)


def cumulative_nf_db(nf_list_db: list, gain_list_db: list) -> list:
    """
    Stage-by-stage cumulative NF [dB] — useful for waterfall plots.
    Returns a list of length N (one entry per stage).
    """
    nf_lin   = [10 ** (n / 10) for n in nf_list_db]
    gain_lin = [10 ** (g / 10) for g in gain_list_db]
    F        = nf_lin[0]
    cum_g    = gain_lin[0]
    result   = [10 * np.log10(F)]
    for i in range(1, len(nf_lin)):
        F     += (nf_lin[i] - 1) / cum_g
        cum_g *= gain_lin[i]
        result.append(10 * np.log10(F))
    return result


def cumulative_gain_db(gain_list_db: list) -> list:
    """Stage-by-stage cumulative gain [dB]."""
    total = 0.0
    result = []
    for g in gain_list_db:
        total += g
        result.append(total)
    return result


def receiver_sensitivity_dbm(
    bw_hz:      float,
    nf_db:      float,
    snr_min_db: float,
    temp_k:     float = T_STD,
) -> float:
    """
    Minimum detectable signal [dBm].
      S_min = kTB + NF + SNR_min
    """
    return thermal_noise_dbm(bw_hz, temp_k) + nf_db + snr_min_db
