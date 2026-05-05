"""Shared configuration — constants, thresholds, tickers, and paths.

All project-wide constants are centralized here.
Imported by core, data_collection, chart modules, and tests.
"""

import datetime
from pathlib import Path

# ---------------------
# Project Paths
# ---------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = (
    _PROJECT_ROOT / "data"
    if (_PROJECT_ROOT / "data").exists()
    else Path.cwd() / "data"
)

# ---------------------
# Regime Classification Thresholds (YoY rates)
# ---------------------
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

# ---------------------
# Data Collection Configuration
# ---------------------
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

# ---------------------
# UI Configuration
# ---------------------
PLOTLY_TEMPLATE = "plotly_dark"

# Assets shown in the correlation matrix
CORR_ASSETS = [
    "S&P 500",
    "Nasdaq 100",
    "MSCI EM",
    "Nominal Bonds",
    "Gold",
    "Crude Oil",
    "Dollar Index",
    "TIPS",
]

# US Treasury FRED code → maturity in years
US_MATURITY_MAP = {
    "DTB4WK": 1 / 12,
    "DGS3MO": 0.25,
    "DGS6MO": 0.5,
    "DGS1": 1,
    "DGS2": 2,
    "DGS3": 3,
    "DGS5": 5,
    "DGS7": 7,
    "DGS10": 10,
    "DGS20": 20,
    "DGS30": 30,
}

# NBER recession periods (for chart overlays)
RECESSIONS = [
    ("2001-03-01", "2001-11-01"),  # Dot-com
    ("2007-12-01", "2009-06-01"),  # Great Financial Crisis
    ("2020-02-01", "2020-04-01"),  # COVID-19
]

# Official ICE DXY basket weights
DXY_WEIGHTS = {
    "EUR": 0.576,
    "JPY": 0.136,
    "GBP": 0.119,
    "CAD": 0.091,
    "SEK": 0.042,
    "CHF": 0.036,
}
