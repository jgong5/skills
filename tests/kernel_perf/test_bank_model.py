"""The bank model is the skill's only executable claim, so it is pinned here.

The expected values are not invented: they are what the profiler measured on a
real gfx942 rocWMMA GEMM. At LDA=32 rocprofv3 reported 82% of LDS cycles as
conflict cycles (an 8x read conflict with conflict-free stores); at LDA=40 it
reported 50% (2x on both). If this test fails, either the model drifted or the
grouping rule in modelling.md is wrong.
"""
import pytest

from bank_model import conflict_factor, cycles, ideal


def frag_read(lda):
    """16x16x16 A/B fragment: lane l takes 4 halves at (l%16)*lda + 4*(l/16)."""
    return lambda l: ((l % 16) * lda + 4 * (l // 16)) * 2


def staging_store(lda):
    """Staging store: thread t writes 8 halves at (t/4)*lda + (t%4)*8."""
    return lambda l: ((l // 4) * lda + (l % 4) * 8) * 2


@pytest.mark.parametrize("width,expected", [(4, 2), (8, 4), (16, 8)])
def test_ideal_tracks_access_width(width, expected):
    assert ideal(width) == expected


def test_power_of_two_stride_is_the_worst_case_for_reads():
    # 32 elements = 64 B = half the bank array: sixteen lanes on two bank pairs.
    assert conflict_factor(frag_read(32), 8) == 8


def test_padding_to_36_clears_the_read():
    assert conflict_factor(frag_read(36), 8) == 1


def test_padding_to_40_halves_the_read_conflict_and_costs_the_store():
    assert conflict_factor(frag_read(40), 8) == 2
    assert conflict_factor(staging_store(40), 16) == 2


def test_the_stride_that_fixes_the_read_cannot_carry_a_16B_store():
    # 36 elements = 72 B a row, so odd rows are only 8 B aligned. This is the
    # constraint that forces a narrower store or a swizzled layout.
    with pytest.raises(ValueError, match="unaligned"):
        conflict_factor(staging_store(36), 16)


def test_conflict_free_store_at_a_power_of_two_stride():
    assert conflict_factor(staging_store(32), 16) == 1


def test_wider_access_is_grouped_more_tightly():
    # Contiguous 16 B per lane: 8 lanes cover the 32 banks exactly once.
    assert cycles(lambda l: l * 16, 16) == ideal(16)


def test_unaligned_address_is_rejected_rather_than_silently_modelled():
    with pytest.raises(ValueError, match="unaligned"):
        cycles(lambda l: l * 16 + 2, 16)
