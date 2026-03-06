"""Core business logic — regime classification, thresholds, and data loading.

This module contains NO Streamlit or Plotly dependencies.
It can be imported by tests and scripts without side effects.
"""

import pandas as pd
from pathlib import Path

# Resolve the project root and data directory
# Use __file__ location first, fall back to cwd if data/ not found there
_FILE_DIR = Path(__file__).resolve().parent
DATA_DIR = _FILE_DIR / "data" if (_FILE_DIR / "data").exists() else Path.cwd() / "data"

# -----------------------------
# Regime Classification Thresholds (YoY rates)
# -----------------------------
# Calibrated on actual US data: GDP YoY median ~4.5%, CPI YoY median ~2.3%
GROWTH_HIGH = 0.04  # GDP YoY above 4% = strong growth
GROWTH_LOW = 0.02  # GDP YoY below 2% = weak growth
INFLATION_HIGH = 0.03  # CPI YoY above 3% = high inflation
INFLATION_LOW = 0.025  # CPI YoY below 2.5% = moderate/low inflation

# Regime color palette
REGIME_COLORS = {
    "Goldilocks": "#2ecc71",  # green
    "Overheating": "#e74c3c",  # red
    "Stagflation": "#e67e22",  # orange
    "Reflation": "#3498db",  # blue
    "Deflation": "#9b59b6",  # purple
}


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
