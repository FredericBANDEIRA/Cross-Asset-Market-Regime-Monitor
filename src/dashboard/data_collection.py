"""Data collection pipeline — Yahoo Finance, FRED, and ECB.

Downloads market data, macro indicators, yield curves, and FX rates.
Writes output as Parquet files (with CSV fallback for futures term structure).
"""

import datetime
import functools
import io
import logging
import time

import pandas as pd
import requests
import yfinance as yf
from dateutil.relativedelta import relativedelta

from dashboard.config import (
    ASSETS,
    DATA_DIR,
    ECB_MATURITIES,
    ECB_MATURITY_YEARS,
    END_DATE,
    FUTURES_CONTRACTS,
    G10_FX,
    MONTH_CODES,
    SHORT_RATES,
    START_DATE,
    YIELD_SERIES_US,
)

logger = logging.getLogger(__name__)


# ---------------------
# Retry Decorator
# ---------------------


def _retry(max_attempts=3, base_delay=1.0):
    """Retry decorator with exponential backoff.

    Retries on any Exception, doubling the delay each attempt.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "%s attempt %d/%d failed: %s — retrying in %.1fs",
                            func.__name__,
                            attempt,
                            max_attempts,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


# ---------------------
# Data Validation
# ---------------------


def _validate_dataframe(df, source_label, min_rows=10):
    """Validate a fetched DataFrame. Returns the df if valid, empty DataFrame if not."""
    if df.empty:
        logger.warning("Validation failed for %s: DataFrame is empty", source_label)
        return pd.DataFrame()

    # Check for all-NaN columns and drop them
    all_nan_cols = df.columns[df.isna().all()].tolist()
    if all_nan_cols:
        logger.warning(
            "Validation: dropping %d all-NaN columns from %s: %s",
            len(all_nan_cols),
            source_label,
            all_nan_cols,
        )
        df = df.drop(columns=all_nan_cols)

    if df.empty:
        logger.warning(
            "Validation failed for %s: no valid columns remain after dropping NaNs",
            source_label,
        )
        return pd.DataFrame()

    if len(df) < min_rows:
        logger.warning(
            "Validation warning for %s: only %d rows (expected >= %d)",
            source_label,
            len(df),
            min_rows,
        )

    return df


# ---------------------
# FRED Fetcher (with retry)
# ---------------------


@_retry(max_attempts=3, base_delay=1.0)
def _fetch_fred_single(sid, start_date):
    """Download a single FRED series via the public CSV endpoint."""
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={sid}&cosd={start_date}"
    )
    df = pd.read_csv(url, index_col=0, parse_dates=True, na_values=["."])
    df.columns = [sid]
    return df


def _fetch_fred(symbols, start_date):
    """Download FRED series directly via the public CSV endpoint.

    This replaces pandas_datareader, which is broken with pandas >= 2.2.
    The FRED graph CSV endpoint is free and requires no API key.
    """
    frames = []
    ids = symbols if isinstance(symbols, list) else [symbols]
    for sid in ids:
        try:
            df = _fetch_fred_single(sid, start_date)
            frames.append(df)
            logger.info("FRED %s: %d rows fetched", sid, len(df))
        except Exception as e:
            logger.error("FRED %s: failed after retries — %s", sid, e)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1)


# ---------------------
# Unified Fetcher
# ---------------------


def fetch_data(tickers, source="yahoo"):
    """Unified downloader with validation."""
    try:
        if source == "yahoo":
            ticker_list = list(tickers.keys()) if isinstance(tickers, dict) else tickers
            logger.info("Fetching %d tickers from Yahoo Finance...", len(ticker_list))
            raw = yf.download(
                ticker_list, start=START_DATE, end=END_DATE, progress=False
            )
            # yfinance returns MultiIndex columns for multi-ticker downloads
            if isinstance(raw.columns, pd.MultiIndex):
                df = raw["Close"]
            elif "Close" in raw.columns:
                df = raw[["Close"]]
                df.columns = ticker_list
            else:
                df = raw
            if isinstance(tickers, dict):
                df = df.rename(columns=tickers)
            df = _validate_dataframe(df, f"Yahoo/{source}")
            return df
        elif source == "fred":
            df = _fetch_fred(tickers, START_DATE)
            df = _validate_dataframe(df, f"FRED/{source}")
            return df
        else:
            raise ValueError(f"Unknown data source: {source}")
    except (ConnectionError, ValueError, KeyError, OSError) as e:
        logger.error("Failed to fetch %s data: %s", source, e)
        return pd.DataFrame()


def process_returns(df):
    """Standardized processing: ffill, dropna, and cumulative calc."""
    cleaned = df.ffill()
    # Drop columns that are entirely NaN (e.g. delisted tickers)
    cleaned = cleaned.dropna(axis=1, how="all")
    # Drop rows where any remaining column is NaN (initial rows)
    cleaned = cleaned.dropna()
    returns = cleaned.pct_change().fillna(0)
    cumulative = (1 + returns).cumprod()
    return cumulative


# ---------------------
# Futures Term Structure
# ---------------------


def fetch_futures_term_structure(n_months=8):
    """Build futures term structure by downloading the latest price
    for the next n_months contract expirations of each commodity.
    Returns a DataFrame with columns: commodity, expiry, price, ticker.
    """
    today = datetime.date.today()
    rows = []

    for commodity, info in FUTURES_CONTRACTS.items():
        root = info["root"]
        suffix = info["suffix"]
        logger.info("Fetching futures for %s (%s)...", commodity, root)

        for i in range(n_months):
            target = today + relativedelta(months=i)
            month_code = MONTH_CODES[target.month]
            year_2d = target.strftime("%y")  # e.g. "25"

            ticker = f"{root}{month_code}{year_2d}{suffix}"
            try:
                data = yf.download(ticker, period="5d", progress=False)
                if data.empty:
                    continue
                last_price = (
                    float(data["Close"].iloc[-1].iloc[0])
                    if isinstance(data["Close"].iloc[-1], pd.Series)
                    else float(data["Close"].iloc[-1])
                )
                expiry_label = target.strftime("%b %Y")  # e.g. "Jun 2025"
                rows.append(
                    {
                        "commodity": commodity,
                        "expiry": expiry_label,
                        "expiry_date": target.replace(day=1).isoformat(),
                        "ticker": ticker,
                        "price": last_price,
                    }
                )
            except Exception as exc:
                logger.debug("Futures %s: skipped — %s", ticker, exc)
                continue

    df = pd.DataFrame(rows)
    logger.info("Futures term structure: %d contracts fetched", len(df))
    return df


# ---------------------
# ECB Yield Curves (with retry)
# ---------------------


@_retry(max_attempts=3, base_delay=2.0)
def _fetch_ecb_single(label, instrument):
    """Fetch a single ECB yield curve dataset."""
    mats = "+".join(ECB_MATURITIES)
    base = "https://data-api.ecb.europa.eu/service/data/YC"
    url = f"{base}/B.U2.EUR.4F.{instrument}.SV_C_YM.{mats}?startPeriod={START_DATE}&format=csvdata"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text))
    # Pivot: rows=date, columns=maturity, values=yield
    pivot = raw.pivot_table(
        index="TIME_PERIOD", columns="DATA_TYPE_FM", values="OBS_VALUE"
    )
    # Rename columns from SR_10Y -> 10 (years)
    pivot = pivot.rename(columns=ECB_MATURITY_YEARS)
    pivot = pivot[sorted(pivot.columns)]  # Sort by maturity
    pivot.index = pd.to_datetime(pivot.index)
    pivot.index.name = "Date"
    return pivot


def fetch_ecb_yield_curves():
    """Fetch Eurozone government bond yield curves from the ECB Data Portal.
    Returns two DataFrames:
    - AAA-rated curve (≈ German Bunds)
    - All-rated curve (broader composite, includes France-level credits)
    Each row = one date, columns = maturity in years.
    """
    results = {}

    for label, instrument in [
        ("Eurozone AAA (~Germany)", "G_N_A"),
        ("Eurozone All (~France)", "G_N_C"),
    ]:
        try:
            pivot = _fetch_ecb_single(label, instrument)
            results[label] = pivot
            logger.info("ECB %s: %d days of data", label, len(pivot))
        except Exception as e:
            logger.error("ECB %s: failed after retries — %s", label, e)
            results[label] = pd.DataFrame()

    return results


# ---------------------
# Pipeline — writes Parquet files
# ---------------------


def run_pipeline():
    """Execute the full data collection pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("Starting data refresh...")
    DATA_DIR.mkdir(exist_ok=True)

    # A. Financial Assets
    logger.info("=== Fetching financial assets ===")
    raw_assets = fetch_data(ASSETS, source="yahoo")
    asset_performance = process_returns(raw_assets)
    asset_performance.to_parquet(DATA_DIR / "all_data.parquet")
    logger.info("Assets: %d rows, %d columns saved", len(asset_performance), asset_performance.shape[1])

    # B. Macro & Volatility - SAVE RAW DATA
    logger.info("=== Fetching macro data ===")
    macro_series = {"CPIAUCNS": "Inflation", "GDP": "Growth", "VIXCLS": "Volatility"}
    macro_data = fetch_data(list(macro_series.keys()), source="fred")
    macro_clean = macro_data.ffill().dropna()
    macro_clean.to_parquet(DATA_DIR / "macro.parquet")
    # Save VIX separately for the dedicated volatility chart
    macro_clean[["VIXCLS"]].to_parquet(DATA_DIR / "vix.parquet")
    logger.info("Macro: %d rows saved", len(macro_clean))

    # C. US Treasury Yields (FRED)
    logger.info("=== Fetching US Treasury yields ===")
    yield_data = fetch_data(YIELD_SERIES_US, source="fred")
    yield_data.ffill().to_parquet(DATA_DIR / "sovereign_yields.parquet")
    logger.info("US yields: %d rows saved", len(yield_data))

    # D. Futures Term Structures
    logger.info("=== Fetching futures term structures ===")
    term_structure = fetch_futures_term_structure()
    # Keep as CSV — small file with mixed types (strings + floats)
    term_structure.to_csv(DATA_DIR / "futures_term_structure.csv", index=False)
    logger.info("Futures: %d contracts saved", len(term_structure))

    # E. ECB Yield Curves (Germany ~ AAA, France ~ All)
    logger.info("=== Fetching ECB yield curves ===")
    ecb_curves = fetch_ecb_yield_curves()
    for label, df in ecb_curves.items():
        safe_name = label.split("(")[0].strip().replace(" ", "_").lower()
        if not df.empty:
            df.to_parquet(DATA_DIR / f"ecb_yields_{safe_name}.parquet")
        logger.info("ECB %s: %d rows saved", label, len(df))

    # F. Macro Indicators (Fed Funds, Credit Spread, Breakeven Inflation)
    logger.info("=== Fetching macro indicators ===")
    indicator_tickers = ["DFF", "BAA10Y", "DFII10"]
    indicators = fetch_data(indicator_tickers, source="fred")
    if not indicators.empty:
        indicators.ffill().to_parquet(DATA_DIR / "macro_indicators.parquet")
        logger.info("Indicators: %d rows saved", len(indicators))

    # G. G10 FX Rates (raw spot prices vs USD)
    logger.info("=== Fetching G10 FX rates ===")
    fx_raw = fetch_data(G10_FX, source="yahoo")
    if not fx_raw.empty:
        fx_raw.ffill().to_parquet(DATA_DIR / "fx_rates.parquet")
        logger.info("FX: %d pairs, %d days saved", fx_raw.shape[1], len(fx_raw))

    # H. G10 Short-Term Interest Rates (for carry indicator)
    logger.info("=== Fetching G10 short-term rates ===")
    short_rates = fetch_data(list(SHORT_RATES.keys()), source="fred")
    if not short_rates.empty:
        short_rates = short_rates.rename(columns=SHORT_RATES)
        short_rates.ffill().to_parquet(DATA_DIR / "short_rates.parquet")
        logger.info("Short rates: %d series, %d rows saved", short_rates.shape[1], len(short_rates))

    logger.info("Pipeline finished. Data updated for %s.", END_DATE)


if __name__ == "__main__":
    run_pipeline()
