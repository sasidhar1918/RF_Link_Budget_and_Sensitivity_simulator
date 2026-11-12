"""
tests/test_core.py
───────────────────
Unit tests for core/ modules.
Run with:  pytest tests/  (from the rf_simulator/ directory)

These tests work with ZERO GUI — proving the math is isolated.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest

from core.friis      import free_space_path_loss_db, received_power_dbm, eirp_dbm, max_range_m
from core.noise      import thermal_noise_dbm, cascaded_nf_db, cumulative_nf_db, receiver_sensitivity_dbm
from core.linearity  import cascaded_oip3_dbm, iip3_from_oip3_dbm, spur_free_dynamic_range_db
from core.path_loss  import okumura_hata, cost231_hata, free_space
from core.modulation import ber_vs_snr, snr_for_ber_target


# ─── Friis ───────────────────────────────────────────────────────────────────

class TestFriis:

    def test_fspl_1km_24ghz(self):
        """Classic spot check: 1km at 2.4 GHz ≈ 100 dB."""
        pl = free_space_path_loss_db(2.4e9, 1000)
        assert abs(pl - 100.05) < 0.1, f"Expected ~100 dB, got {pl:.2f}"

    def test_fspl_increases_with_distance(self):
        pl_1km = free_space_path_loss_db(1e9, 1000)
        pl_2km = free_space_path_loss_db(1e9, 2000)
        assert pl_2km > pl_1km

    def test_fspl_doubles_6db_per_octave(self):
        """FSPL increases by exactly 20·log10(2) ≈ 6.0206 dB when distance doubles."""
        expected = 20 * np.log10(2)          # 6.0206 dB — exact Friis result
        pl_d  = free_space_path_loss_db(1e9, 1000)
        pl_2d = free_space_path_loss_db(1e9, 2000)
        assert abs((pl_2d - pl_d) - expected) < 1e-6

    def test_fspl_doubles_6db_per_octave_freq(self):
        """FSPL increases by exactly 20·log10(2) ≈ 6.0206 dB when frequency doubles."""
        expected = 20 * np.log10(2)
        pl_f  = free_space_path_loss_db(1e9, 1000)
        pl_2f = free_space_path_loss_db(2e9, 1000)
        assert abs((pl_2f - pl_f) - expected) < 1e-6

    def test_received_power_decreases_with_distance(self):
        p1 = received_power_dbm(30, 15, 5, 2.4e9, 1000)
        p2 = received_power_dbm(30, 15, 5, 2.4e9, 5000)
        assert p2 < p1

    def test_eirp(self):
        assert eirp_dbm(30, 15, 1.5) == pytest.approx(43.5, abs=0.01)

    def test_max_range_positive(self):
        r = max_range_m(30, 15, 5, 2.4e9, -90)
        assert r > 0

    def test_fspl_vectorised(self):
        d = np.array([100, 1000, 10000])
        pl = free_space_path_loss_db(2.4e9, d)
        assert pl.shape == (3,)
        assert np.all(np.diff(pl) > 0)   # monotone increasing


# ─── Noise ────────────────────────────────────────────────────────────────────

class TestNoise:

    def test_thermal_noise_floor_20mhz(self):
        """kTB at 20 MHz BW ≈ -101 dBm."""
        n = thermal_noise_dbm(20e6)
        assert abs(n - (-101.0)) < 0.5

    def test_thermal_noise_increases_with_bw(self):
        assert thermal_noise_dbm(100e6) > thermal_noise_dbm(10e6)

    def test_cascaded_nf_single_stage(self):
        """Single stage: cascaded NF = that stage's NF."""
        nf = cascaded_nf_db([5.0], [20.0])
        assert abs(nf - 5.0) < 0.01

    def test_cascaded_nf_lna_dominates(self):
        """High-gain LNA first: cascaded NF ≈ LNA NF."""
        nf = cascaded_nf_db([1.5, 8.0], [30.0, 10.0])
        assert nf < 2.0   # second stage contribution negligible

    def test_cascaded_nf_loss_first_hurts(self):
        """Attenuator first: raises cascaded NF significantly."""
        nf_with_loss   = cascaded_nf_db([6.0, 1.5], [-6.0, 30.0])
        nf_lna_first   = cascaded_nf_db([1.5, 6.0], [30.0, -6.0])
        assert nf_with_loss > nf_lna_first

    def test_cascaded_nf_mismatched_lengths(self):
        with pytest.raises(ValueError):
            cascaded_nf_db([5.0, 3.0], [10.0])

    def test_cumulative_nf_length(self):
        result = cumulative_nf_db([2, 5, 8], [20, 10, 5])
        assert len(result) == 3

    def test_sensitivity_ktb_plus_nf_plus_snr(self):
        sens = receiver_sensitivity_dbm(20e6, 5.0, 10.0)
        floor = thermal_noise_dbm(20e6)
        assert abs(sens - (floor + 5.0 + 10.0)) < 0.01


# ─── Linearity ───────────────────────────────────────────────────────────────

class TestLinearity:

    def test_oip3_single_stage(self):
        """Single stage OIP3 = that stage's OIP3."""
        assert abs(cascaded_oip3_dbm([25.0], [10.0]) - 25.0) < 0.01

    def test_oip3_limited_by_weakest(self):
        """A very non-linear stage dominates the cascade."""
        good = cascaded_oip3_dbm([40.0, 40.0, 10.0], [10.0, 10.0, 10.0])
        assert good < 20.0

    def test_oip3_two_stage_hand_calc(self):
        """Stage 1: 10 dB gain, 20 dBm OIP3. Stage 2: 10 dB gain, 30 dBm OIP3.
        1/OIP3 = 1/OIP3_2 + 1/(OIP3_1 * G2) = 1/1000 + 1/(100 * 10) per mW
        OIP3 = 500 mW = 26.99 dBm."""
        result = cascaded_oip3_dbm([20.0, 30.0], [10.0, 10.0])
        assert result == pytest.approx(26.99, abs=0.01)

    def test_oip3_never_exceeds_last_stage(self):
        """The cascade cannot be better than the last stage's own OIP3."""
        assert cascaded_oip3_dbm([20.0, 30.0], [10.0, 10.0]) <= 30.0

    def test_iip3_from_oip3(self):
        assert iip3_from_oip3_dbm(25.0, 20.0) == pytest.approx(5.0, abs=0.01)

    def test_sfdr_positive(self):
        sfdr = spur_free_dynamic_range_db(25.0, -101.0)
        assert sfdr > 0


# ─── Path Loss ────────────────────────────────────────────────────────────────

class TestPathLoss:

    def test_oh_urban_increases_with_distance(self):
        pl1 = okumura_hata(900, 1.0)
        pl5 = okumura_hata(900, 5.0)
        assert pl5 > pl1

    def test_cost231_higher_than_oh_same_freq(self):
        """COST-231 large city should be higher than COST-231 medium."""
        pl_med   = cost231_hata(1800, 2.0, city="medium")
        pl_large = cost231_hata(1800, 2.0, city="large")
        assert pl_large > pl_med

    def test_fspl_less_than_oh_urban(self):
        """Free space underestimates urban environment."""
        pl_fs = free_space(1800e6, 2000)      # 2 km
        pl_oh = okumura_hata(1800, 2.0)
        assert pl_oh > pl_fs

    def test_vectorised_oh(self):
        d = np.linspace(1, 20, 50)
        pl = okumura_hata(900, d)
        assert pl.shape == (50,)
        assert np.all(np.diff(pl) > 0)


# ─── Modulation / BER ─────────────────────────────────────────────────────────

class TestModulation:

    def test_ber_bpsk_0db_is_high(self):
        ber = ber_vs_snr(np.array([1.0]), "BPSK")[0]
        assert ber > 0.05

    def test_ber_decreases_with_snr(self):
        snr = np.array([1, 2, 5, 10, 20])
        ber = ber_vs_snr(10 ** (snr / 10), "BPSK")
        assert np.all(np.diff(ber) < 0)

    def test_bpsk_qpsk_same_ber(self):
        snr_lin = np.array([10.0])
        assert abs(ber_vs_snr(snr_lin, "BPSK")[0]
                   - ber_vs_snr(snr_lin, "QPSK")[0]) < 1e-12

    def test_higher_order_needs_more_snr(self):
        """64QAM needs more SNR than QPSK for same BER."""
        snr_qpsk  = snr_for_ber_target(1e-3, "QPSK")
        snr_64qam = snr_for_ber_target(1e-3, "64QAM")
        assert snr_64qam > snr_qpsk

    def test_unknown_modulation_raises(self):
        with pytest.raises(ValueError):
            ber_vs_snr(np.array([10.0]), "AM")

    def test_snr_for_ber_bpsk_1e3(self):
        """BPSK needs ~6.8 dB for BER=10⁻³."""
        snr = snr_for_ber_target(1e-3, "BPSK")
        assert 6.5 < snr < 7.5
