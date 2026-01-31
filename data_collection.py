import pandas as pd
import yfinance as yf
import pandas_datareader.data as dr
import datetime

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
    "TIP": "Inflation-linked Bonds", # Added missing metric 
    "GC=F": "Gold",
    "CL=F": "Crude Oil",
    "ZW=F": "Wheat",
    "DX=F": "Dollar"
}

# Yield curves: US and German [cite: 6, 14]
YIELD_SERIES = {
    "US":  [
    "DTB4WK", "DGS3MO", "DGS6MO",  # Short-term (for the 1-month Treasury: DGS1MO is not available)
    "DGS1", "DGS2", "DGS3",        # Medium-term  
    "DGS5", "DGS7", "DGS10",       # Long-term
    "DGS20", "DGS30"               # Very long-term
],
    "GER": ["IRLTLT01DEM156N"] # German 10Y (Long-term)
}

# -----------------------------
# 2. Refactored Functions
# -----------------------------

def fetch_data(tickers, source="yahoo"):
    """Unified downloader for better error handling."""
    if source == "yahoo":
        # Using list(tickers.keys()) for efficiency
        df = yf.download(list(tickers.keys()), start=START_DATE, end=END_DATE, progress=False)["Close"]
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

    print(f"Pipeline finished. Data updated for {END_DATE}.")

if __name__ == "__main__":
    run_pipeline()