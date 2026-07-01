"""Python reference model for the QPSK bit-to-symbol mapper.

CCSDS 401.0-B-32, Section 2.4.10:
  - bits[1] (MSB) → I channel via NRZ-L
  - bits[0] (LSB) → Q channel via NRZ-L
  - NRZ-L: 0 → +amplitude,  1 → -amplitude
  - SCALE_16BIT = 23170 = round(32767 / sqrt(2))  [unit energy, 16-bit signed]
"""

from __future__ import annotations

SCALE_16BIT = 23170


def map_qpsk_symbol(bits: tuple[int, int], amplitude: int = SCALE_16BIT) -> tuple[int, int]:
    """Map two bits to a signed I/Q symbol pair.

    Args:
        bits: (MSB, LSB) where MSB in {0,1} and LSB in {0,1}.
        amplitude: per-component scale; default is SCALE_16BIT (23170).

    Returns:
        (i_out, q_out), each equal to +amplitude or -amplitude.

    Symbol table (CCSDS 401.0-B-32 s.2.4.10):
        MSB LSB | I        Q       phase
         0   0  | +amp    +amp     45°
         0   1  | +amp    -amp    315°
         1   0  | -amp    +amp    135°
         1   1  | -amp    -amp    225°
    """
    if bits[0] not in (0, 1) or bits[1] not in (0, 1):
        raise ValueError(f"bits must be (0 or 1, 0 or 1), got {bits}")

    msb, lsb = bits
    i_out = amplitude if msb == 0 else -amplitude
    q_out = amplitude if lsb == 0 else -amplitude
    return (i_out, q_out)
