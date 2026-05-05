import pandas as pd
import yfinance as yf
import datetime
import io
import requests
from dateutil.relativedelta import relativedelta
from core import DATA_DIR


def _fetch_fred(symbols, start_date):
    """Download FRED series directly via the public CSV endpoint.

    This replaces pandas_datareader, which is broken with pandas >= 2.2.
    The FRED graph CSV endpoint is free and requires no API key.
    """
    frames = []
    ids = symbols if isinstance(symbols, list) else [symbols]
    for sid in ids:
        url = (
            f"https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id={sid}&cosd={start_date}"
        )
        try:
            df = pd.read_csv(url, index_col=0, parse_dates=True, na_values=["."])
            df.columns = [sid]
            frames.append(df)
        except Exception as e:
            print(f"  [x] FRED {sid}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1)

# -----------------------------
# 1. Configuration (Centralized)
# -----------------------------
# Updated start date for 2024/25 Academic Year requirements
START_DATE = "2000-01-01"
END_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# Core asset classes
ASSETS = {
    # Equities — US
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    # Equities — International
    "^FCHI": "CAC 40",
    "^FTSE": "FTSE 100",
    "^GDAXI": "DAX",
    "^N225": "Nikkei 225",
    "EFA": "MSCI EAFE",
    "EEM": "MSCI EM",
    # Bonds
    "TLT": "Nominal Bonds",
    "TIP": "TIPS",
    # Commodities
    "GC=F": "Gold",
    "SI=F": "Silver",
    "CL=F": "Crude Oil",
    "NG=F": "Natural Gas",
    "HG=F": "Copper",
    "ZW=F": "Wheat",
    # Dollar
    "DX-Y.NYB": "Dollar Index",
}

# G10 FX pairs (all vs USD, Yahoo Finance format)
G10_FX = {
    "EURUSD=X": "EUR",
    "GBPUSD=X": "GBP",
    "USDJPY=X": "JPY",
    "USDCHF=X": "CHF",
    "AUDUSD=X": "AUD",
    "NZDUSD=X": "NZD",
    "USDCAD=X": "CAD",
    "USDNOK=X": "NOK",
    "USDSEK=X": "SEK",
}

# G10 short-term interest rates (FRED) — for carry indicator
# Policy / interbank rates; best available proxies
SHORT_RATES = {
    "DFF": "USD",  # US Federal Funds Rate
    "IRSTCI01JPM156N": "JPY",  # Japan call rate (monthly)
    "IR3TIB01GBM156N": "GBP",  # UK 3-month interbank rate
    "ECBDFR": "EUR",  # ECB deposit facility rate
    "IR3TIB01CAM156N": "CAD",  # Canada 3-month interbank
    "IR3TIB01CHM156N": "CHF",  # Switzerland 3-month interbank
    "IR3TIB01AUM156N": "AUD",  # Australia 3-month interbank
    "IR3TIB01NZM156N": "NZD",  # New Zealand 3-month interbank
    "IR3TIB01NOM156N": "NOK",  # Norway 3-month interbank
    "IR3TIB01SEM156N": "SEK",  # Sweden 3-month interbank
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
            raw = yf.download(
                list(tickers.keys()), start=START_DATE, end=END_DATE, progress=False
            )
            # yfinance returns MultiIndex columns for multi-ticker downloads
            if isinstance(raw.columns, pd.MultiIndex):
                df = raw["Close"]
            elif "Close" in raw.columns:
                df = raw[["Close"]]
                df.columns = list(tickers.keys())
            else:
                df = raw
            return df.rename(columns=tickers)
        elif source == "fred":
            df = _fetch_fred(tickers, START_DATE)
            return df
        else:
            raise ValueError(f"Unknown data source: {source}")
    except (ConnectionError, ValueError, KeyError, OSError) as e:
        print(f"  [X] Failed to fetch {source} data: {e}")
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
                last_price = float(data["Close"].iloc[-1].iloc[0]) if isinstance(data["Close"].iloc[-1], pd.Series) else float(data["Close"].iloc[-1])
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
        ("Eurozone AAA (~Germany)", "G_N_A"),
        ("Eurozone All (~France)", "G_N_C"),
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
            print(f"  -> {label}: {len(pivot)} days of data")
        except Exception as e:
            print(f"  [X] {label}: {e}")
            results[label] = pd.DataFrame()

    return results


# -----------------------------
# 3. Execution Logic (The 'Clean' Workflow)
# -----------------------------


def run_pipeline():
    print("Starting data refresh...")
    DATA_DIR.mkdir(exist_ok=True)

    # A. Financial Assets
    raw_assets = fetch_data(ASSETS, source="yahoo")
    asset_performance = process_returns(raw_assets)
    asset_performance.to_csv(DATA_DIR / "all_data.csv", sep=";")

    # B. Macro & Volatility - SAVE RAW DATA
    macro_series = {"CPIAUCNS": "Inflation", "GDP": "Growth", "VIXCLS": "Volatility"}
    macro_data = fetch_data(list(macro_series.keys()), source="fred")
    macro_clean = macro_data.ffill().dropna()
    macro_clean.to_csv(DATA_DIR / "macro.csv")
    # Save VIX separately for the dedicated volatility chart
    macro_clean[["VIXCLS"]].to_csv(DATA_DIR / "vix.csv")

    # C. US Treasury Yields (FRED)
    yield_data = fetch_data(YIELD_SERIES_US, source="fred")
    yield_data.ffill().to_csv(DATA_DIR / "sovereign_yields.csv")

    # D. Futures Term Structures
    print("Fetching futures term structures...")
    term_structure = fetch_futures_term_structure()
    term_structure.to_csv(DATA_DIR / "futures_term_structure.csv", index=False)
    print(f"  -> {len(term_structure)} contracts fetched.")

    # E. ECB Yield Curves (Germany ~ AAA, France ~ All)
    print("Fetching ECB yield curves...")
    ecb_curves = fetch_ecb_yield_curves()
    for label, df in ecb_curves.items():
        safe_name = label.split("(")[0].strip().replace(" ", "_").lower()
        df.to_csv(DATA_DIR / f"ecb_yields_{safe_name}.csv")

    # F. Macro Indicators (Fed Funds, Credit Spread, Breakeven Inflation)
    print("Fetching macro indicators...")
    indicator_tickers = ["DFF", "BAA10Y", "DFII10"]
    indicators = fetch_data(indicator_tickers, source="fred")
    if not indicators.empty:
        indicators.ffill().to_csv(DATA_DIR / "macro_indicators.csv")
        print(f"  -> {len(indicators)} rows of macro indicators")

    # G. G10 FX Rates (raw spot prices vs USD)
    print("Fetching G10 FX rates...")
    fx_raw = fetch_data(G10_FX, source="yahoo")
    if not fx_raw.empty:
        fx_raw.ffill().to_csv(DATA_DIR / "fx_rates.csv")
        print(f"  -> {fx_raw.shape[1]} FX pairs, {len(fx_raw)} days")

    # H. G10 Short-Term Interest Rates (for carry indicator)
    print("Fetching G10 short-term rates...")
    short_rates = fetch_data(list(SHORT_RATES.keys()), source="fred")
    if not short_rates.empty:
        short_rates = short_rates.rename(columns=SHORT_RATES)
        short_rates.ffill().to_csv(DATA_DIR / "short_rates.csv")
        print(f"  -> {short_rates.shape[1]} rate series, {len(short_rates)} rows")

    print(f"Pipeline finished. Data updated for {END_DATE}.")


if __name__ == "__main__":
    run_pipeline()
