"""Tests for core data loading and cleaning logic."""

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from dashboard.core import load_and_clean_data, classify_regime, _read_data_file


# ----- _read_data_file tests -----


class TestReadDataFile:
    """Tests for the Parquet-first, CSV-fallback file reader."""

    def test_prefers_parquet_over_csv(self, tmp_path):
        """When both .parquet and .csv exist, should read .parquet."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df_parquet = pd.DataFrame({"A": [1, 2, 3, 4, 5]}, index=dates)
        df_csv = pd.DataFrame({"A": [10, 20, 30, 40, 50]}, index=dates)

        df_parquet.to_parquet(tmp_path / "test.parquet")
        df_csv.to_csv(tmp_path / "test.csv")

        with patch("dashboard.core.DATA_DIR", tmp_path):
            result = _read_data_file("test")

        # Should read parquet values, not csv
        assert result["A"].iloc[0] == 1

    def test_falls_back_to_csv(self, tmp_path):
        """When only .csv exists (no .parquet), should read .csv."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({"A": [10, 20, 30, 40, 50]}, index=dates)
        df.to_csv(tmp_path / "test.csv")

        with patch("dashboard.core.DATA_DIR", tmp_path):
            result = _read_data_file("test")

        assert result["A"].iloc[0] == 10

    def test_returns_empty_when_no_file(self, tmp_path):
        """When neither .parquet nor .csv exists, returns empty DataFrame."""
        with patch("dashboard.core.DATA_DIR", tmp_path):
            result = _read_data_file("nonexistent")

        assert result.empty


# ----- load_and_clean_data tests -----


class TestLoadAndCleanData:
    """Tests for the main data loader."""

    @pytest.fixture
    def mock_data_dir(self, tmp_path):
        """Create minimal data files in a temp directory."""
        dates = pd.date_range("2020-01-01", periods=500, freq="D")

        # Macro data — needs GDP, CPIAUCNS, VIXCLS
        macro = pd.DataFrame(
            {
                "GDP": np.linspace(20000, 25000, 500),
                "CPIAUCNS": np.linspace(250, 270, 500),
                "VIXCLS": np.random.uniform(15, 30, 500),
            },
            index=dates,
        )
        macro.to_parquet(tmp_path / "macro.parquet")

        # Asset data
        assets = pd.DataFrame(
            {
                "S&P 500": np.linspace(1.0, 1.5, 500),
                "Gold": np.linspace(1.0, 1.2, 500),
            },
            index=dates,
        )
        assets.to_parquet(tmp_path / "all_data.parquet")

        # VIX
        vix = pd.DataFrame({"VIXCLS": np.random.uniform(15, 30, 500)}, index=dates)
        vix.to_parquet(tmp_path / "vix.parquet")

        # US Yields
        yields_df = pd.DataFrame(
            {"DGS10": np.linspace(2.0, 4.0, 500), "DGS2": np.linspace(1.5, 3.5, 500)},
            index=dates,
        )
        yields_df.to_parquet(tmp_path / "sovereign_yields.parquet")

        return tmp_path

    def test_returns_correct_tuple_length(self, mock_data_dir):
        """load_and_clean_data should return a 12-element tuple."""
        with patch("dashboard.core.DATA_DIR", mock_data_dir):
            result = load_and_clean_data()

        assert isinstance(result, tuple)
        assert len(result) == 12

    def test_all_elements_are_dataframes(self, mock_data_dir):
        """Every element in the returned tuple should be a DataFrame."""
        with patch("dashboard.core.DATA_DIR", mock_data_dir):
            result = load_and_clean_data()

        for i, element in enumerate(result):
            assert isinstance(element, pd.DataFrame), f"Element {i} is {type(element)}"

    def test_macro_yoy_has_regime_column(self, mock_data_dir):
        """The macro_yoy DataFrame (last element) should have a Regime column."""
        with patch("dashboard.core.DATA_DIR", mock_data_dir):
            result = load_and_clean_data()

        macro_yoy = result[-1]  # Last element
        if not macro_yoy.empty:
            assert "Regime" in macro_yoy.columns

    def test_macro_yoy_regimes_are_valid(self, mock_data_dir):
        """All regime labels should be from the expected set."""
        valid_regimes = {"Goldilocks", "Overheating", "Stagflation", "Reflation", "Deflation"}
        with patch("dashboard.core.DATA_DIR", mock_data_dir):
            result = load_and_clean_data()

        macro_yoy = result[-1]
        if not macro_yoy.empty:
            actual_regimes = set(macro_yoy["Regime"].unique())
            assert actual_regimes.issubset(valid_regimes)

    def test_handles_missing_optional_files(self, mock_data_dir):
        """Should not crash when optional files (ECB, FX, etc.) are missing."""
        # mock_data_dir doesn't have ECB, FX, futures, indicators, short_rates
        with patch("dashboard.core.DATA_DIR", mock_data_dir):
            result = load_and_clean_data()

        # ECB, futures, indicators, FX, short_rates should be empty DataFrames
        ecb_aaa = result[5]
        ecb_all = result[6]
        futures = result[7]
        indicators = result[8]
        fx_rates = result[9]
        short_rates = result[10]

        assert ecb_aaa.empty
        assert ecb_all.empty
        assert futures.empty
        assert indicators.empty
        assert fx_rates.empty
        assert short_rates.empty

    def test_handles_corrupt_macro_file(self, tmp_path):
        """Should not crash if a required file is corrupt."""
        # Write garbage to macro file
        (tmp_path / "macro.csv").write_text("this,is,not,valid\ndata")

        # Write minimal asset data so it doesn't crash on that
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        assets = pd.DataFrame({"A": [1, 2, 3, 4, 5]}, index=dates)
        assets.to_parquet(tmp_path / "all_data.parquet")

        with patch("dashboard.core.DATA_DIR", tmp_path):
            result = load_and_clean_data()

        # Should return a tuple without crashing
        assert isinstance(result, tuple)
        assert len(result) == 12
