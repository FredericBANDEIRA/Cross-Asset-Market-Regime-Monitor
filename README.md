# Cross-Asset Market Regime Monitor

A Streamlit dashboard that classifies the macroeconomic environment into **five regimes** (Goldilocks, Overheating, Stagflation, Reflation, Deflation) and tracks cross-asset performance across each.

## Features

### Dashboard Tabs

| Tab                           | Contents                                                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| 📊 **Overview**               | Regime timeline, cross-asset correlation matrix, performance heatmap                          |
| 📈 **Macro & Rates**          | GDP/CPI trends, VIX, breakeven inflation, credit spread, Fed Funds rate, regime decomposition |
| 🏦 **Fixed Income**           | Sovereign yield curves (US/Eurozone), 10Y–2Y inversion indicator                              |
| 💹 **Equities & Commodities** | Cumulative returns (rebased), futures term structures                                         |
| 💱 **FX**                     | G10 cross-rates matrix                                                                        |

### Key Capabilities

- **Regime Classification** — GDP × CPI YoY thresholds computed on monthly-resampled data, with color-coded timeline
- **Regime Decomposition** — GDP YoY vs CPI YoY chart with threshold reference lines for full transparency
- **KPI Dashboard** — Current regime badge, VIX, US 10Y yield, 30-day equity return (always visible above tabs)
- **22 Assets** — US & international equities, bonds, commodities, FX, dollar index
- **Sovereign Yield Curves** — US Treasury (FRED), Eurozone AAA ≈ Germany, Eurozone All ≈ France (ECB API)
- **10Y–2Y Spread** — Classic inversion indicator with shaded inversion periods
- **Futures Term Structure** — Contango/backwardation for 5 commodity/index futures
- **G10 FX Cross Rates** — 10×10 matrix computed from USD pairs
- **Macro Indicators** — Breakeven inflation, credit spread (Baa–10Y), Federal Funds rate
- **Sidebar Filters** — Time range presets (1W–Max), custom date range, asset selection, regime filter

## Data Sources

| Source          | Data                                      | Frequency       |
| --------------- | ----------------------------------------- | --------------- |
| Yahoo Finance   | Asset prices, futures contracts, FX rates | Daily           |
| FRED            | US yields, CPI, GDP, VIX, Fed Funds, Baa  | Daily / Monthly |
| ECB Data Portal | Eurozone government bond yield curves     | Daily           |

## Installation

```bash
# Clone and install
git clone https://github.com/<your-username>/Cross-Asset-Market-Regime-Monitor.git
cd Cross-Asset-Market-Regime-Monitor
uv sync

# Fetch data (required on first run)
uv run python data_collection.py

# Launch dashboard
uv run streamlit run ui_design.py
```

## Project Structure

```
├── data_collection.py    # Data pipeline (Yahoo, FRED, ECB)
├── ui_design.py          # Streamlit dashboard (tabbed layout)
├── pyproject.toml        # Dependencies
├── tests/                # Unit tests
└── .github/workflows/    # Daily data refresh (GitHub Actions)
```

## Regime Definitions

| Regime         | GDP YoY | CPI YoY | Interpretation                           |
| -------------- | ------- | ------- | ---------------------------------------- |
| 🟢 Goldilocks  | > 4%    | < 2.5%  | Strong growth, low inflation             |
| 🔴 Overheating | > 2%    | ≥ 2.5%  | Moderate-to-strong growth, rising prices |
| 🟠 Stagflation | ≤ 2%    | ≥ 3%    | Weak growth, high inflation              |
| 🔵 Reflation   | > 2%    | < 2.5%  | Moderate growth, low inflation           |
| 🟣 Deflation   | ≤ 2%    | < 2.5%  | Weak growth, low inflation               |

> Thresholds calibrated on actual US GDP/CPI distributions (2004–2025).
> YoY changes computed on monthly-resampled data to avoid artifacts from quarterly GDP reporting.

## Assets Tracked

**Equities:** S&P 500, Nasdaq 100, Russell 2000, CAC 40, FTSE 100, DAX, Nikkei 225, MSCI EAFE, MSCI EM

**Fixed Income:** US Nominal Bonds (TLT), TIPS (TIP)

**Commodities:** Gold, Silver, Crude Oil, Natural Gas, Copper, Wheat

**FX:** EUR, GBP, JPY, CHF, AUD, NZD, CAD, NOK, SEK (vs USD)

**Other:** Dollar Index (DXY)
