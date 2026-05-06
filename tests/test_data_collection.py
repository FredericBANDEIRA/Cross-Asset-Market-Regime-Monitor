"""Tests for data processing logic."""

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from dashboard.data_collection import process_returns, _validate_dataframe, _retry
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
    assert not result.iloc[1:].isna().any().any()


def test_process_returns_drops_all_nan_columns():
    """Columns that are entirely NaN should be dropped."""
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    df = pd.DataFrame({"A": [100] * 5, "B": [np.nan] * 5}, index=dates)
    result = process_returns(df)
    assert "B" not in result.columns
    assert "A" in result.columns


# ----- MONTH_CODES config tests -----


def test_month_codes_completeness():
    assert len(MONTH_CODES) == 12
    assert set(MONTH_CODES.keys()) == set(range(1, 13))


def test_month_codes_unique():
    codes = list(MONTH_CODES.values())
    assert len(set(codes)) == 12
    assert all(len(c) == 1 and c.isalpha() for c in codes)


# ----- _validate_dataframe tests -----


def test_validate_returns_empty_for_empty_df():
    result = _validate_dataframe(pd.DataFrame(), "test")
    assert result.empty


def test_validate_drops_all_nan_columns():
    df = pd.DataFrame({"A": [1, 2, 3], "B": [np.nan] * 3})
    result = _validate_dataframe(df, "test")
    assert "B" not in result.columns
    assert "A" in result.columns


def test_validate_returns_empty_when_all_columns_nan():
    df = pd.DataFrame({"A": [np.nan, np.nan], "B": [np.nan, np.nan]})
    result = _validate_dataframe(df, "test")
    assert result.empty


def test_validate_warns_on_few_rows():
    df = pd.DataFrame({"A": [1, 2, 3]})
    result = _validate_dataframe(df, "test", min_rows=100)
    assert len(result) == 3


def test_validate_passes_good_data():
    df = pd.DataFrame({"A": range(100), "B": range(100)})
    result = _validate_dataframe(df, "test")
    assert len(result) == 100


# ----- _retry decorator tests -----


def test_retry_succeeds_on_first_attempt():
    call_count = 0

    @_retry(max_attempts=3, base_delay=0.01)
    def succeed():
        nonlocal call_count
        call_count += 1
        return "ok"

    assert succeed() == "ok"
    assert call_count == 1


def test_retry_succeeds_on_second_attempt():
    call_count = 0

    @_retry(max_attempts=3, base_delay=0.01)
    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("temp")
        return "ok"

    assert flaky() == "ok"
    assert call_count == 2


def test_retry_raises_after_max_attempts():
    @_retry(max_attempts=3, base_delay=0.01)
    def always_fail():
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        always_fail()


# ----- Mocked fetcher tests -----


def test_fetch_fred_single_success():
    from dashboard.data_collection import _fetch_fred_single

    mock_df = pd.DataFrame(
        {"CPIAUCNS": [257.971, 258.678]},
        index=pd.to_datetime(["2020-01-01", "2020-02-01"]),
    )
    with patch("dashboard.data_collection.pd.read_csv", return_value=mock_df):
        result = _fetch_fred_single.__wrapped__("CPIAUCNS", "2020-01-01")
    assert not result.empty


def test_fetch_fred_single_retries():
    """The _retry decorator around _fetch_fred_single should retry on failure."""
    from dashboard.data_collection import _fetch_fred_single

    call_count = 0

    def flaky_read(*a, **kw):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("down")
        return pd.DataFrame({"X": [1]}, index=pd.to_datetime(["2020-01-01"]))

    with patch("dashboard.data_collection.pd.read_csv", side_effect=flaky_read):
        # Call the decorated function (not __wrapped__) — retries should kick in
        result = _fetch_fred_single("X", "2020-01-01")
    assert call_count == 3
    assert not result.empty
