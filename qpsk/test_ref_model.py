"""Unit tests for the QPSK reference model.

Covers all four constellation points, default and custom amplitude,
and invalid input rejection.
"""

import pytest
from ref_model import map_qpsk_symbol, SCALE_16BIT


# ── All four CCSDS constellation points (CCSDS 401.0-B-32, s.2.4.10) ─────────

def test_00_maps_to_pos_i_pos_q():
    assert map_qpsk_symbol((0, 0)) == (SCALE_16BIT, SCALE_16BIT)

def test_01_maps_to_pos_i_neg_q():
    assert map_qpsk_symbol((0, 1)) == (SCALE_16BIT, -SCALE_16BIT)

def test_10_maps_to_neg_i_pos_q():
    assert map_qpsk_symbol((1, 0)) == (-SCALE_16BIT, SCALE_16BIT)

def test_11_maps_to_neg_i_neg_q():
    assert map_qpsk_symbol((1, 1)) == (-SCALE_16BIT, -SCALE_16BIT)


# ── Scale = 23170 matches unit-energy normalization ────────────────────────────

def test_scale_value():
    assert SCALE_16BIT == 23170

def test_all_points_same_magnitude():
    for msb in (0, 1):
        for lsb in (0, 1):
            i, q = map_qpsk_symbol((msb, lsb))
            assert abs(i) == SCALE_16BIT
            assert abs(q) == SCALE_16BIT


# ── Custom amplitude ───────────────────────────────────────────────────────────

def test_custom_amplitude_1():
    assert map_qpsk_symbol((0, 0), amplitude=1) == (1, 1)
    assert map_qpsk_symbol((1, 1), amplitude=1) == (-1, -1)

def test_custom_amplitude_32767():
    i, q = map_qpsk_symbol((0, 0), amplitude=32767)
    assert i == 32767 and q == 32767


# ── Invalid inputs rejected ────────────────────────────────────────────────────

def test_invalid_bits_raises():
    with pytest.raises(ValueError):
        map_qpsk_symbol((2, 0))
    with pytest.raises(ValueError):
        map_qpsk_symbol((0, -1))
