"""Smoke tests for chart rendering modules.

These tests call each chart's render() function with minimal synthetic data.
They verify that the code doesn't crash (no visual assertions).
Streamlit calls are mocked to avoid the need for a running server.
"""

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


# ---------------------
# Shared Fixtures
# ---------------------


@pytest.fixture
def dates():
    return pd.date_range("2020-01-01", periods=100, freq="D")


@pytest.fixture
def cum_returns(dates):
    np.random.seed(42)
    return pd.DataFrame(
        {
            "S&P 500": np.cumprod(1 + np.random.normal(0.0005, 0.01, 100)),
            "Nasdaq 100": np.cumprod(1 + np.random.normal(0.0006, 0.012, 100)),
            "Gold": np.cumprod(1 + np.random.normal(0.0002, 0.008, 100)),
            "Nominal Bonds": np.cumprod(1 + np.random.normal(0.0001, 0.005, 100)),
            "Dollar Index": np.cumprod(1 + np.random.normal(0.0001, 0.004, 100)),
            "MSCI EM": np.cumprod(1 + np.random.normal(0.0003, 0.011, 100)),
            "Crude Oil": np.cumprod(1 + np.random.normal(0.0002, 0.015, 100)),
            "TIPS": np.cumprod(1 + np.random.normal(0.0001, 0.004, 100)),
        },
        index=dates,
    )


@pytest.fixture
def macro_yoy(dates):
    return pd.DataFrame(
        {
            "GDP": np.random.uniform(0.01, 0.05, 100),
            "CPIAUCNS": np.random.uniform(0.01, 0.04, 100),
            "Regime": np.random.choice(
                ["Goldilocks", "Overheating", "Reflation"], 100
            ),
        },
        index=dates,
    )


@pytest.fixture
def yields_us(dates):
    return pd.DataFrame(
        {
            "DGS10": np.linspace(2.0, 4.0, 100),
            "DGS2": np.linspace(1.5, 3.5, 100),
            "DGS30": np.linspace(2.5, 4.5, 100),
        },
        index=dates,
    )


@pytest.fixture
def indicators(dates):
    return pd.DataFrame(
        {
            "DFF": np.linspace(0.5, 5.0, 100),
            "BAA10Y": np.linspace(1.5, 3.0, 100),
            "DFII10": np.linspace(0.0, 2.0, 100),
        },
        index=dates,
    )


@pytest.fixture
def fx_rates(dates):
    return pd.DataFrame(
        {
            "EUR": np.linspace(1.10, 1.15, 100),
            "GBP": np.linspace(1.25, 1.30, 100),
            "JPY": np.linspace(110, 115, 100),
            "CHF": np.linspace(0.90, 0.95, 100),
        },
        index=dates,
    )


@pytest.fixture
def short_rates(dates):
    return pd.DataFrame(
        {
            "USD": np.linspace(0.5, 5.0, 100),
            "EUR": np.linspace(0.0, 3.0, 100),
            "GBP": np.linspace(0.25, 4.5, 100),
            "JPY": np.linspace(-0.1, 0.1, 100),
        },
        index=dates,
    )


@pytest.fixture
def start_dt(dates):
    return dates[0]


@pytest.fixture
def end_dt(dates):
    return dates[-1]


# ---------------------
# Smoke Tests — using monkeypatch to avoid @patch arg injection issues
# ---------------------


_ST_PATCHES = [
    "streamlit.plotly_chart",
    "streamlit.subheader",
    "streamlit.caption",
    "streamlit.dataframe",
    "streamlit.info",
    "streamlit.warning",
    "streamlit.divider",
]


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Patch common Streamlit functions for all smoke tests."""
    patches = [patch(p) for p in _ST_PATCHES]
    for p in patches:
        p.start()
    # st.columns needs to return context managers
    col_patch = patch(
        "streamlit.columns",
        return_value=[MagicMock(), MagicMock()],
    )
    col_patch.start()
    patches.append(col_patch)

    yield

    for p in patches:
        p.stop()


def test_overview_render(cum_returns, macro_yoy, start_dt, end_dt):
    """Overview tab should not crash with valid data."""
    from dashboard.charts import overview

    overview.render(
        cum_returns=cum_returns,
        macro_yoy=macro_yoy,
        display_assets=cum_returns,
        start_dt=start_dt,
        end_dt=end_dt,
        selected_regime="All",
    )


def test_macro_render(cum_returns, macro_yoy, yields_us, indicators, start_dt, end_dt):
    """Macro tab should not crash with valid data."""
    from dashboard.charts import macro

    macro_trends = cum_returns[["S&P 500", "Gold"]].rename(
        columns={"S&P 500": "GDP", "Gold": "CPIAUCNS"}
    )
    vola = pd.DataFrame(
        {"VIXCLS": np.random.uniform(15, 30, 100)}, index=cum_returns.index
    )
    macro.render(
        macro_trends=macro_trends,
        vola=vola,
        indicators=indicators,
        yields_us=yields_us,
        macro_yoy=macro_yoy,
        start_dt=start_dt,
        end_dt=end_dt,
    )


@patch("streamlit.select_slider", return_value="2020-04-09")
@patch("streamlit.radio", return_value="US Treasury")
def test_fixed_income_render(mock_radio, mock_slider, yields_us, indicators, start_dt, end_dt):
    """Fixed Income tab should not crash with valid data."""
    from dashboard.charts import fixed_income

    fixed_income.render(
        yields_us=yields_us,
        ecb_aaa=pd.DataFrame(),
        ecb_all=pd.DataFrame(),
        indicators=indicators,
        start_dt=start_dt,
        end_dt=end_dt,
    )


@patch("streamlit.multiselect", return_value=["S&P 500", "Gold"])
@patch("streamlit.selectbox", return_value="Gold")
def test_equities_render(mock_select, mock_multi, cum_returns, start_dt, end_dt):
    """Equities tab should not crash with valid data."""
    from dashboard.charts import equities

    equities.render(
        display_assets=cum_returns,
        selected_assets=["S&P 500", "Gold"],
        selected_regime="All",
        futures_ts=pd.DataFrame(),
        cum_returns=cum_returns,
        start_dt=start_dt,
        end_dt=end_dt,
    )


@patch("streamlit.multiselect", return_value=["EUR", "GBP"])
def test_fx_render(mock_multi, fx_rates, short_rates, start_dt, end_dt):
    """FX tab should not crash with valid data."""
    from dashboard.charts import fx

    fx.render(
        fx_rates=fx_rates,
        short_rates=short_rates,
        start_dt=start_dt,
        end_dt=end_dt,
    )
