import pytest

from agentops.stats import is_thin, wilson


def test_wilson_known_values():
    zero = wilson(0, 10)
    assert zero.mean == 0 and zero.low == 0 and zero.high == pytest.approx(0.278, abs=0.002)
    half = wilson(5, 10)
    assert half.low == pytest.approx(0.237, abs=0.002)
    assert half.high == pytest.approx(0.763, abs=0.002)
    assert half.n_items == 10


def test_wilson_n_zero_is_uninformative():
    r = wilson(0, 0)
    assert (r.mean, r.low, r.high, r.n_items) == (0, 0, 1, 0)


def test_thin_sample_boundary():
    assert is_thin(19) and not is_thin(20)
