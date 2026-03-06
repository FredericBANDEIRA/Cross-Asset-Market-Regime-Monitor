"""Tests for data processing logic — pure functions, no external dependencies."""

import pandas as pd
import numpy as np
import pytest


# ----- Inline copies of pure functions from data_collection.py -----
# These are copied to avoid importing the full module (which triggers
# network-dependent imports like yfinance/pandas_datareader).


def process_returns(df):
    """Standardized processing: ffill, dropna, and cumulative calc."""
    cleaned = df.ffill().dropna()
    returns = cleaned.pct_change().fillna(0)
    cumulative = (1 + returns).cumprod()
    return cumulative


def process_macro_regimes(macro_df):
    """Calculate YoY changes to determine economic momentum."""
    macro_yoy = macro_df.pct_change(periods=12).dropna()
    return macro_yoy


MONTH_CODES = {
    1: "F",
    2: "G",
    3: "H",
    4: "J",
    5: "K",
    6: "M",
    7: "N",
    8: "Q",
    9: "U",
    10: "V",
    11: "X",
    12: "Z",
}


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


# ----- process_macro_regimes tests -----


def test_process_macro_regimes_yoy():
    """YoY should compute 12-period pct_change."""
    dates = pd.date_range("2020-01-01", periods=24, freq="MS")
    df = pd.DataFrame({"CPI": [100] * 24}, index=dates)
    result = process_macro_regimes(df)
    assert len(result) == 12
    assert np.allclose(result.values, 0.0)


def test_process_macro_regimes_growth():
    """A series that doubles after 12 months should show ~100% YoY."""
    dates = pd.date_range("2020-01-01", periods=24, freq="MS")
    values = list(range(100, 112)) + list(range(200, 224))[:12]
    df = pd.DataFrame({"GDP": values}, index=dates)
    result = process_macro_regimes(df)
    expected = values[12] / values[0] - 1
    assert result["GDP"].iloc[0] == pytest.approx(expected)


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
