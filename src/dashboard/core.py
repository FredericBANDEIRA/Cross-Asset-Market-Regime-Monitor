"""Core business logic — regime classification and data loading.

This module contains NO Streamlit or Plotly dependencies.
It can be imported by tests and scripts without side effects.
"""

import logging

import pandas as pd

from dashboard.config import (
    DATA_DIR,
    GROWTH_HIGH,
    GROWTH_LOW,
    INFLATION_HIGH,
    INFLATION_LOW,
)

logger = logging.getLogger(__name__)


def classify_regime(row):
    """Determines regime based on YoY thresholds.

    Clean decision tree — every GDP/CPI combination maps to exactly one regime:

      Strong growth  (GDP > 4%):  Goldilocks  if CPI < 2.5%, else Overheating
      Moderate growth (2-4%):     Reflation   if CPI < 2.5%, else Overheating
      Weak growth    (GDP ≤ 2%):  Deflation   if CPI < 3%,   else Stagflation
    """
    g = row.get("GDP", 0)
    i = row.get("CPIAUCNS", 0)

    if g > GROWTH_HIGH:
        # Strong growth
        return "Goldilocks" if i < INFLATION_LOW else "Overheating"
    elif g > GROWTH_LOW:
        # Moderate growth
        return "Reflation" if i < INFLATION_LOW else "Overheating"
    else:
        # Weak growth (g <= GROWTH_LOW)
        return "Deflation" if i < INFLATION_HIGH else "Stagflation"


def _read_data_file(name, *, index_col=0, parse_dates=True, **kwargs):
    """Read a data file, preferring Parquet over CSV for backward compatibility.

    Looks for ``<name>.parquet`` first; falls back to ``<name>.csv`` if the
    Parquet file does not exist.  Returns ``(DataFrame, path_used)``.
    """
    parquet_path = DATA_DIR / f"{name}.parquet"
    csv_path = DATA_DIR / f"{name}.csv"

    if parquet_path.exists():
        logger.debug("Loading %s (parquet)", name)
        return pd.read_parquet(parquet_path)
    elif csv_path.exists():
        logger.debug("Loading %s (csv fallback)", name)
        return pd.read_csv(
            csv_path, index_col=index_col, parse_dates=parse_dates, **kwargs
        )
    else:
        logger.warning("Data file not found: %s (.parquet or .csv)", name)
        return pd.DataFrame()


def load_and_clean_data():
    """Loads all datasets from the data/ directory and handles initial cleaning.

    Returns a tuple of DataFrames in a fixed order.  The YoY regime
    classification is computed here so it is covered by the Streamlit cache.
    """
    # 1. Macro Data: Load RAW levels
    try:
        macro_raw = _read_data_file("macro")
        macro_raw = macro_raw.apply(pd.to_numeric, errors="coerce").ffill().dropna()
        logger.info("Macro data loaded: %d rows", len(macro_raw))
    except Exception as exc:
        logger.error("Failed to load macro data: %s", exc)
        macro_raw = pd.DataFrame()

    # Create growth index for visualization
    if not macro_raw.empty:
        macro_idx = (1 + macro_raw.pct_change().fillna(0)).cumprod()
    else:
        macro_idx = pd.DataFrame()

    # 2. Asset Data
    try:
        assets = _read_data_file("all_data", delimiter=";")
        assets = assets.ffill().dropna()
        logger.info("Asset data loaded: %d rows, %d assets", len(assets), assets.shape[1])
    except Exception as exc:
        logger.error("Failed to load asset data: %s", exc)
        assets = pd.DataFrame()

    # 3. Volatility
    try:
        vola = _read_data_file("vix")
        vola = vola.ffill().dropna()
    except Exception as exc:
        logger.error("Failed to load VIX data: %s", exc)
        vola = pd.DataFrame()

    # 4. US Yields
    try:
        yields_us = _read_data_file("sovereign_yields")
        yields_us = yields_us.ffill().dropna()
    except Exception as exc:
        logger.error("Failed to load US yield data: %s", exc)
        yields_us = pd.DataFrame()

    # 5. ECB Yield Curves (optional)
    ecb_aaa = _read_data_file("ecb_yields_eurozone_aaa")
    ecb_all = _read_data_file("ecb_yields_eurozone_all")

    # 6. Futures Term Structure (optional — always CSV, mixed types)
    futures_path = DATA_DIR / "futures_term_structure.csv"
    futures_ts = pd.read_csv(futures_path) if futures_path.exists() else pd.DataFrame()

    # 7. Macro Indicators (optional)
    indicators = _read_data_file("macro_indicators")
    if not indicators.empty:
        indicators = indicators.ffill()

    # 8. G10 FX Rates (optional)
    fx_rates = _read_data_file("fx_rates")
    if not fx_rates.empty:
        fx_rates = fx_rates.ffill().dropna()

    # 9. G10 Short-Term Interest Rates (optional)
    short_rates = _read_data_file("short_rates")
    if not short_rates.empty:
        short_rates = short_rates.ffill()

    # 10. Compute YoY + Regime classification (cached with everything else)
    if not macro_raw.empty:
        macro_monthly = macro_raw.resample("ME").last()
        macro_yoy = macro_monthly.pct_change(12).dropna()
        macro_yoy["Regime"] = macro_yoy.apply(classify_regime, axis=1)
        # Reindex to daily for timeline display (forward-fill monthly regimes)
        macro_yoy = macro_yoy.reindex(macro_raw.index, method="ffill").dropna()
        logger.info(
            "Regime classification complete: %d days, current regime = %s",
            len(macro_yoy),
            macro_yoy["Regime"].iloc[-1] if not macro_yoy.empty else "N/A",
        )
    else:
        macro_yoy = pd.DataFrame()

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
        macro_yoy,
    )
