"""
core/linearity.py
──────────────────
Cascaded OIP3 / IIP3 calculations.
Pure math — zero GUI dependency.
"""

import numpy as np


def cascaded_oip3_dbm(oip3_list_dbm: list, gain_list_db: list) -> float:
    """
    Cascaded Output IP3 [dBm] using the inverse-power-sum approximation.

    The output-referred contribution of each stage is gained up to the
    system output, then summed in inverse (weakest non-linearity dominates):
      1/OIP3_sys = Σ  (G_after_i / OIP3_i)
    """
    if len(oip3_list_dbm) != len(gain_list_db):
        raise ValueError("oip3_list and gain_list must have the same length.")
    n        = len(oip3_list_dbm)
    oip3_lin = [10 ** (o / 10) for o in oip3_list_dbm]
    gain_lin = [10 ** (g / 10) for g in gain_list_db]

    # cumulative gain from stage i+1 to the output
    cum_gain_after = [1.0] * n
    for i in range(n - 2, -1, -1):
        cum_gain_after[i] = cum_gain_after[i + 1] * gain_lin[i + 1]

    inv_oip3 = sum(cum_gain_after[i] / oip3_lin[i] for i in range(n))
    return 10 * np.log10(1.0 / inv_oip3)


def iip3_from_oip3_dbm(oip3_dbm: float, total_gain_db: float) -> float:
    """Input IP3 = OIP3 - total gain  [dBm]."""
    return oip3_dbm - total_gain_db


def spur_free_dynamic_range_db(
    oip3_dbm: float,
    noise_floor_dbm: float,
) -> float:
    """
    SFDR = (2/3) · (OIP3 - noise_floor)  [dB].
    """
    return (2 / 3) * (oip3_dbm - noise_floor_dbm)


def p1db_from_oip3(oip3_dbm: float, offset_db: float = 9.6) -> float:
    """
    Approximate 1-dB compression point from OIP3.
    Typical rule: OP1dB ≈ OIP3 - 9.6 dB
    """
    return oip3_dbm - offset_db
