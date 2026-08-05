"""The probe's measurements need a GPU, but its interpretation does not.

The sweeps below are real: they are what the triton read kernel measured on an
MI308X (gfx942), whose 256 MB memory-attached last level neither rocminfo nor
torch reports. Both runs must yield the same capacity, because the point of
comparing plateau against asymptote is that it survives the run-to-run wobble
in any single adjacent-size step.
"""
import pytest

# The probe defines triton kernels at module scope, so importing it needs both.
# The logic under test needs neither -- skip rather than fail in a checkout
# without a GPU stack.
pytest.importorskip("torch")
pytest.importorskip("triton")

from probe_roofline import FLOP_PER_CLK_PER_CU, cache_estimate, flop_per_clk  # noqa: E402

SIZES = (32, 64, 128, 192, 256, 320, 384, 512, 1024, 2048, 4096)

# Two measured sweeps of the same part. The step out of cache is 1.31x in one
# and 1.14x in the other -- a single-step threshold would have to sit below
# 1.14 to catch both, which is inside the noise of a flat sweep.
SHARP = (2.36, 4.06, 4.49, 4.69, 4.79, 3.66, 3.47, 3.47, 3.36, 3.42, 3.37)
GRADUAL = (2.36, 4.06, 4.47, 4.67, 4.79, 4.21, 4.17, 4.01, 3.71, 3.49, 3.42)

# Indices whose measured duration was long enough to trust (32 and 64 MiB ran
# in ~15 us, where fixed launch cost understates the rate).
ELIGIBLE = set(range(2, len(SIZES)))


@pytest.mark.parametrize("rates", [SHARP, GRADUAL], ids=["sharp", "gradual"])
def test_both_measured_sweeps_find_the_256_mib_last_level(rates):
    assert cache_estimate(SIZES, rates, ELIGIBLE) == 256


def test_a_flat_sweep_reports_no_cache():
    flat = tuple(3.40 + 0.03 * (i % 3) for i in range(len(SIZES)))
    assert cache_estimate(SIZES, flat, ELIGIBLE) is None


def test_overhead_bound_sizes_cannot_set_the_plateau():
    # If the understated 32 MiB row were eligible it would drag the asymptote
    # comparison around; excluded, the answer is unchanged.
    assert cache_estimate(SIZES, GRADUAL, ELIGIBLE) == 256


def test_a_sweep_too_short_to_interpret_returns_none():
    assert cache_estimate((256,), (4.79,), {0}) is None


def test_capacity_is_the_last_size_at_plateau_not_the_first_to_fall():
    # 256 MiB is still at cache rate; 320 is the first that is not. Reporting
    # 320 would overstate the cache by one sweep step.
    assert cache_estimate(SIZES, GRADUAL, ELIGIBLE) != 320


@pytest.mark.parametrize("arch,expected", sorted(FLOP_PER_CLK_PER_CU.items()))
def test_known_architectures_have_a_constant(arch, expected):
    assert flop_per_clk(arch) == expected


def test_gfx942_constant_is_the_measured_one():
    # 4 Matrix Cores x 8192 FLOP / 16 cycles. Verified on MI308X: the cross
    # check in the probe puts torch.mm at 90% of the resulting peak.
    assert flop_per_clk("gfx942") == 2048


def test_an_unknown_architecture_names_the_flag_rather_than_guessing():
    with pytest.raises(KeyError, match="--flop-per-clk"):
        flop_per_clk("gfx1100")


def test_override_wins_over_the_table():
    assert flop_per_clk("gfx942", 4096) == 4096
    assert flop_per_clk("gfx1100", 512) == 512
