"""Core business logic — regime classification and data loading.

This module contains NO Streamlit or Plotly dependencies.
It can be imported by tests and scripts without side effects.
"""

import pandas as pd
from dashboard.config import (
    DATA_DIR,
    GROWTH_HIGH,
    GROWTH_LOW,
    INFLATION_HIGH,
    INFLATION_LOW,
)


def classify_regime(row):
    """Determines regime based on YoY thresholds.

    Quadrant model:
      - Goldilocks:  high growth + low inflation
      - Overheating: high growth + high inflation
      - Stagflation: low growth  + high inflation
      - Reflation:   moderate growth + low inflation
      - Deflation:   low growth  + low inflation
    """
    g = row.get("GDP", 0)
    i = row.get("CPIAUCNS", 0)

    if g > GROWTH_HIGH and i < INFLATION_LOW:
        return "Goldilocks"
    elif g > GROWTH_HIGH and i >= INFLATION_HIGH:
        return "Overheating"
    elif g <= GROWTH_LOW and i >= INFLATION_HIGH:
        return "Stagflation"
    elif g <= GROWTH_LOW and i < INFLATION_LOW:
        return "Deflation"
    elif g > GROWTH_LOW and i < INFLATION_LOW:
        return "Reflation"
    elif g > GROWTH_LOW and i >= INFLATION_LOW:
        return "Overheating"
    else:
        return "Deflation"


def load_and_clean_data():
    """Loads all datasets from the data/ directory and handles initial cleaning.

    Returns a tuple of DataFrames in a fixed order.
    """
    # 1. Macro Data: Load RAW levels
    macro_raw = pd.read_csv(DATA_DIR / "macro.csv", index_col=0, parse_dates=True)
    macro_raw = macro_raw.apply(pd.to_numeric, errors="coerce").ffill().dropna()

    # Create growth index for visualization
    macro_idx = (1 + macro_raw.pct_change().fillna(0)).cumprod()

    # 2. Asset Data
    assets = (
        pd.read_csv(
            DATA_DIR / "all_data.csv", index_col=0, delimiter=";", parse_dates=True
        )
        .ffill()
        .dropna()
    )

    # 3. Volatility
    vola = (
        pd.read_csv(DATA_DIR / "vix.csv", index_col=0, parse_dates=True)
        .ffill()
        .dropna()
    )

    # 4. US Yields
    yields_us = (
        pd.read_csv(DATA_DIR / "sovereign_yields.csv", index_col=0, parse_dates=True)
        .ffill()
        .dropna()
    )

    # 5. ECB Yield Curves (optional)
    ecb_aaa = pd.DataFrame()
    ecb_all = pd.DataFrame()
    aaa_path = DATA_DIR / "ecb_yields_eurozone_aaa.csv"
    all_path = DATA_DIR / "ecb_yields_eurozone_all.csv"
    if aaa_path.exists():
        ecb_aaa = pd.read_csv(aaa_path, index_col=0, parse_dates=True)
    if all_path.exists():
        ecb_all = pd.read_csv(all_path, index_col=0, parse_dates=True)

    # 6. Futures Term Structure (optional)
    futures_path = DATA_DIR / "futures_term_structure.csv"
    futures_ts = pd.read_csv(futures_path) if futures_path.exists() else pd.DataFrame()

    # 7. Macro Indicators (optional)
    indicators_path = DATA_DIR / "macro_indicators.csv"
    if indicators_path.exists():
        indicators = pd.read_csv(indicators_path, index_col=0, parse_dates=True).ffill()
    else:
        indicators = pd.DataFrame()

    # 8. G10 FX Rates (optional)
    fx_path = DATA_DIR / "fx_rates.csv"
    if fx_path.exists():
        fx_rates = pd.read_csv(fx_path, index_col=0, parse_dates=True).ffill().dropna()
    else:
        fx_rates = pd.DataFrame()

    # 9. G10 Short-Term Interest Rates (optional)
    sr_path = DATA_DIR / "short_rates.csv"
    if sr_path.exists():
        short_rates = pd.read_csv(sr_path, index_col=0, parse_dates=True).ffill()
    else:
        short_rates = pd.DataFrame()

    return (
        macro_raw,
        macro_idx,
        assets,
        vola,
        yields_us,
        ecb_aaa,
        ecb_all,
        futures_ts,
        indicators,
        fx_rates,
        short_rates,
    )
