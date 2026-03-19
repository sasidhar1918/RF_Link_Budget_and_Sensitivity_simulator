"""
core/monte_carlo.py
────────────────────
Monte Carlo channel fading simulation.
Models: Rayleigh, Rician, Nakagami-m, AWGN (no fading).
Pure math — zero GUI dependency.
"""

import numpy as np
from dataclasses import dataclass
from typing import Literal


FadingModel = Literal["Rayleigh", "Rician", "Nakagami", "AWGN"]


@dataclass
class FadingResult:
    model:           str
    n_samples:       int
    mean_rx_dbm:     float
    std_db:          float
    outage_prob_pct: float
    p10_dbm:         float   # 10th percentile
    p1_dbm:          float   # 1st  percentile
    samples_dbm:     np.ndarray


def fading_envelope_sq(n: int, model: FadingModel,
                        K_db: float = 6.0,
                        seed: int | None = None) -> np.ndarray:
    """
    Generate n envelope-squared samples (power normalised to 1 on average).

    Returns array where each value is a power scaling factor h² such that
    E[h²] = 1.

    Args:
        seed: Optional RNG seed for reproducibility. Pass None (default)
              for a fresh random seed each call (live simulation mode).
    """
    rng = np.random.default_rng(seed)   # None → random; int → reproducible

    if model == "Rayleigh":
        # |h|² ~ Exp(1)  (two Gaussian components, each σ=1/√2)
        return (rng.standard_normal(n) ** 2
                + rng.standard_normal(n) ** 2) / 2

    elif model == "Rician":
        K    = 10 ** (K_db / 10)
        nu   = np.sqrt(K / (K + 1))          # LOS amplitude
        sg   = np.sqrt(1 / (2 * (K + 1)))    # scatter σ per component
        I    = rng.standard_normal(n) * sg + nu
        Q    = rng.standard_normal(n) * sg
        return I ** 2 + Q ** 2

    elif model == "Nakagami":
        m = max(float(K_db), 0.5)            # m parameter (K_db reused as m)
        # |h|² ~ Gamma(m, 1/m)  → E[h²]=1
        return rng.gamma(m, 1.0 / m, n)

    else:   # AWGN — no fading
        return np.ones(n)


def simulate(
    mean_rx_dbm:     float,
    sensitivity_dbm: float,
    n_samples:       int  = 100_000,
    model:           FadingModel = "Rayleigh",
    K_db:            float = 6.0,
    seed:            int | None = None,
) -> FadingResult:
    """
    Run a Monte Carlo fading simulation and return a FadingResult.

    Args:
        seed: Optional RNG seed. Pass an int for a reproducible run;
              leave as None for a fresh random simulation each call.
    """
    p_mean_mw   = 10 ** (mean_rx_dbm / 10)
    envelope_sq = fading_envelope_sq(n_samples, model, K_db, seed=seed)
    samples_mw  = p_mean_mw * envelope_sq
    samples_dbm = 10 * np.log10(np.maximum(samples_mw, 1e-30))

    outage = float(np.mean(samples_dbm < sensitivity_dbm) * 100)

    return FadingResult(
        model           = model,
        n_samples       = n_samples,
        mean_rx_dbm     = float(np.mean(samples_dbm)),
        std_db          = float(np.std(samples_dbm)),
        outage_prob_pct = outage,
        p10_dbm         = float(np.percentile(samples_dbm, 10)),
        p1_dbm          = float(np.percentile(samples_dbm,  1)),
        samples_dbm     = samples_dbm,
    )
