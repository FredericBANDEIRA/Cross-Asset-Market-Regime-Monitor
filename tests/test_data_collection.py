"""Tests for data processing logic."""

import pandas as pd
import numpy as np
import pytest
from dashboard.data_collection import process_returns
from dashboard.config import MONTH_CODES

# ----- process_returns tests -----


def test_process_returns_basic():
    """Cumulative returns of constant prices should be 1.0 everywhere."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"A": [100, 100, 100, 100, 100]}, index=dates)
    result = process_returns(df)
    assert np.allclose(result.dropna().values, 1.0)


def test_process_returns_known_values():
    """Verify cumulative returns with a simple doubling sequence."""
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    df = pd.DataFrame({"A": [100, 200, 200, 400]}, index=dates)
    result = process_returns(df)
    assert result["A"].iloc[-1] == pytest.approx(4.0)


def test_process_returns_handles_missing():
    """Forward-fill should handle NaN in the middle of data."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"A": [100, np.nan, 100, 100, 100]}, index=dates)
    result = process_returns(df)
    # First row is always NaN from pct_change; after that everything should be filled
    assert not result.iloc[1:].isna().any().any()

# ----- MONTH_CODES config tests -----

def test_month_codes_completeness():
    """All 12 months must be mapped."""
    assert len(MONTH_CODES) == 12
    assert set(MONTH_CODES.keys()) == set(range(1, 13))


def test_month_codes_unique():
    """All month codes must be unique single letters."""
    codes = list(MONTH_CODES.values())
    assert len(set(codes)) == 12
    assert all(len(c) == 1 and c.isalpha() for c in codes)
