import pandas as pd
import yfinance as yf
import pandas_datareader.data as dr
import datetime
import io
import requests
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

# US Treasury yield curve maturities (FRED)
YIELD_SERIES_US = [
    "DTB4WK",
    "DGS3MO",
    "DGS6MO",
    "DGS1",
    "DGS2",
    "DGS3",
    "DGS5",
    "DGS7",
    "DGS10",
    "DGS20",
    "DGS30",
]

# ECB yield curve maturities to fetch
ECB_MATURITIES = [
    "SR_3M",
    "SR_6M",
    "SR_1Y",
    "SR_2Y",
    "SR_3Y",
    "SR_5Y",
    "SR_7Y",
    "SR_10Y",
    "SR_15Y",
    "SR_20Y",
    "SR_30Y",
]

# Map ECB maturity codes to numeric years
ECB_MATURITY_YEARS = {
    "SR_3M": 0.25,
    "SR_6M": 0.5,
    "SR_1Y": 1,
    "SR_2Y": 2,
    "SR_3Y": 3,
    "SR_5Y": 5,
    "SR_7Y": 7,
    "SR_10Y": 10,
    "SR_15Y": 15,
    "SR_20Y": 20,
    "SR_30Y": 30,
}

# -----------------------------
# 2. Refactored Functions
# -----------------------------


def fetch_data(tickers, source="yahoo"):
    """Unified downloader for better error handling."""
    try:
        if source == "yahoo":
            df = yf.download(
                list(tickers.keys()), start=START_DATE, end=END_DATE, progress=False
            )["Close"]
            return df.rename(columns=tickers)
        elif source == "fred":
            df = dr.DataReader(tickers, "fred", START_DATE)
            return df
        else:
            raise ValueError(f"Unknown data source: {source}")
    except Exception as e:
        print(f"  ✗ Failed to fetch {source} data: {e}")
        return pd.DataFrame()


def process_returns(df):
    """Standardized processing: ffill, dropna, and cumulative calc."""
    cleaned = df.ffill().dropna()
    returns = cleaned.pct_change()
    cumulative = (1 + returns).cumprod()
    return cumulative


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


def fetch_ecb_yield_curves():
    """
    Fetch Eurozone government bond yield curves from the ECB Data Portal.
    Returns two DataFrames:
    - AAA-rated curve (≈ German Bunds)
    - All-rated curve (broader composite, includes France-level credits)
    Each row = one date, columns = maturity in years.
    """
    mats = "+".join(ECB_MATURITIES)
    base = "https://data-api.ecb.europa.eu/service/data/YC"
    results = {}

    for label, instrument in [
        ("Eurozone AAA (≈ Germany)", "G_N_A"),
        ("Eurozone All (≈ France)", "G_N_C"),
    ]:
        url = f"{base}/B.U2.EUR.4F.{instrument}.SV_C_YM.{mats}?startPeriod={START_DATE}&format=csvdata"
        try:
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
            results[label] = pivot
            print(f"  → {label}: {len(pivot)} days of data")
        except Exception as e:
            print(f"  ✗ {label}: {e}")
            results[label] = pd.DataFrame()

    return results


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
    macro_clean = macro_data.ffill().dropna()
    macro_clean.to_csv("macro.csv")
    # Save VIX separately for the dedicated volatility chart
    macro_clean[["VIXCLS"]].to_csv("vix.csv")

    # C. US Treasury Yields (FRED)
    yield_data = fetch_data(YIELD_SERIES_US, source="fred")
    yield_data.ffill().to_csv("sovereign_yields.csv")

    # D. Futures Term Structures
    print("Fetching futures term structures...")
    term_structure = fetch_futures_term_structure()
    term_structure.to_csv("futures_term_structure.csv", index=False)
    print(f"  → {len(term_structure)} contracts fetched.")

    # E. ECB Yield Curves (Germany ≈ AAA, France ≈ All)
    print("Fetching ECB yield curves...")
    ecb_curves = fetch_ecb_yield_curves()
    for label, df in ecb_curves.items():
        safe_name = label.split("(")[0].strip().replace(" ", "_").lower()
        df.to_csv(f"ecb_yields_{safe_name}.csv")

    print(f"Pipeline finished. Data updated for {END_DATE}.")


if __name__ == "__main__":
    run_pipeline()
