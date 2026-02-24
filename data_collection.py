import pandas as pd
import yfinance as yf
import pandas_datareader.data as dr
import datetime
from dateutil.relativedelta import relativedelta

# -----------------------------
# 1. Configuration (Centralized)
# -----------------------------
# Updated start date for 2024/25 Academic Year requirements
START_DATE = "2000-01-01"
END_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# asset classes from project scope [cite: 16-22]
ASSETS = {
    "SPY": "Equities",
    "TLT": "Nominal Bonds",
    "TIP": "Inflation-linked Bonds",  # Added missing metric
    "GC=F": "Gold",
    "CL=F": "Crude Oil",
    "ZW=F": "Wheat",
    "DX=F": "Dollar",
}

# Yield curves: US and German [cite: 6, 14]
YIELD_SERIES = {
    "US": [
        "DTB4WK",
        "DGS3MO",
        "DGS6MO",  # Short-term (for the 1-month Treasury: DGS1MO is not available)
        "DGS1",
        "DGS2",
        "DGS3",  # Medium-term
        "DGS5",
        "DGS7",
        "DGS10",  # Long-term
        "DGS20",
        "DGS30",  # Very long-term
    ],
    "GER": ["IRLTLT01DEM156N"],  # German 10Y (Long-term)
}

# -----------------------------
# 2. Refactored Functions
# -----------------------------


def fetch_data(tickers, source="yahoo"):
    """Unified downloader for better error handling."""
    if source == "yahoo":
        # Using list(tickers.keys()) for efficiency
        df = yf.download(
            list(tickers.keys()), start=START_DATE, end=END_DATE, progress=False
        )["Close"]
        return df.rename(columns=tickers)
    elif source == "fred":
        df = dr.DataReader(tickers, "fred", START_DATE)
        return df


def process_returns(df):
    """Standardized processing: ffill, dropna, and cumulative calc."""
    cleaned = df.ffill().dropna()
    returns = cleaned.pct_change()
    cumulative = (1 + returns).cumprod()
    return cumulative


def process_macro_regimes(macro_df):
    """Calculate YoY changes to determine economic momentum."""
    # GDP is quarterly, CPI is monthly; we calculate % change from 1 year ago
    macro_yoy = macro_df.pct_change(periods=12).dropna()
    return macro_yoy


# CME month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun,
#                  N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
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

# Commodity root symbols and their Yahoo Finance exchange suffix
FUTURES_CONTRACTS = {
    "Gold": {"root": "GC", "suffix": ".CMX"},
    "Crude Oil": {"root": "CL", "suffix": ".NYM"},
    "Wheat": {"root": "ZW", "suffix": ".CBT"},
    "Dollar": {"root": "DX", "suffix": ".NYB"},
    "S&P 500": {"root": "ES", "suffix": ".CME"},
}


def fetch_futures_term_structure(n_months=8):
    """
    Build futures term structure by downloading the latest price
    for the next n_months contract expirations of each commodity.
    Returns a DataFrame with columns: commodity, expiry, price, ticker.
    """
    today = datetime.date.today()
    rows = []

    for commodity, info in FUTURES_CONTRACTS.items():
        root = info["root"]
        suffix = info["suffix"]

        for i in range(n_months):
            target = today + relativedelta(months=i)
            month_code = MONTH_CODES[target.month]
            year_2d = target.strftime("%y")  # e.g. "25"

            ticker = f"{root}{month_code}{year_2d}{suffix}"
            try:
                data = yf.download(ticker, period="5d", progress=False)
                if data.empty:
                    continue
                last_price = float(data["Close"].iloc[-1])
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
            except Exception:
                continue  # Silently skip unavailable contracts

    df = pd.DataFrame(rows)
    return df


# -----------------------------
# 3. Execution Logic (The 'Clean' Workflow)
# -----------------------------


def run_pipeline():
    print("Starting data refresh...")

    # A. Financial Assets
    raw_assets = fetch_data(ASSETS, source="yahoo")
    asset_performance = process_returns(raw_assets)
    asset_performance.to_csv("all_data.csv", sep=";")

    # B. Macro & Volatility - SAVE RAW DATA
    macro_series = {"CPIAUCNS": "Inflation", "GDP": "Growth", "VIXCLS": "Volatility"}
    macro_data = fetch_data(list(macro_series.keys()), source="fred")
    # Save raw levels directly so UI can compute YoY correctly
    macro_data.ffill().dropna().to_csv("macro.csv")

    # C. Sovereign Yields
    all_yield_tickers = YIELD_SERIES["US"] + YIELD_SERIES["GER"]
    yield_data = fetch_data(all_yield_tickers, source="fred")
    yield_data.ffill().to_csv("sovereign_yields.csv")

    # D. Futures Term Structures
    print("Fetching futures term structures...")
    term_structure = fetch_futures_term_structure()
    term_structure.to_csv("futures_term_structure.csv", index=False)
    print(f"  → {len(term_structure)} contracts fetched.")

    print(f"Pipeline finished. Data updated for {END_DATE}.")


if __name__ == "__main__":
    run_pipeline()
