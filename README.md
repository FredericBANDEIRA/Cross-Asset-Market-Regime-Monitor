# Cross-Asset Market Regime Monitor

A Streamlit dashboard that classifies the macroeconomic environment into **five regimes** (Goldilocks, Overheating, Stagflation, Reflation, Deflation) and tracks cross-asset performance across each.

## Features

- **Regime Classification** — GDP × Inflation YoY thresholds with color-coded timeline
- **KPI Dashboard** — current regime, VIX, US 10Y yield, 30-day equity return
- **Asset Performance** — cumulative returns for 7 asset classes (equities, bonds, gold, oil, wheat, dollar, TIPS), filterable by regime
- **Sovereign Yield Curves** — US Treasury (FRED), Eurozone AAA ≈ Germany, Eurozone All ≈ France (ECB API)
- **10Y – 2Y Spread** — classic inversion indicator with shaded inversion periods
- **Futures Term Structure** — contango/backwardation for 5 commodity/index futures
- **Performance Heatmap** — period returns at a glance

## Data Sources

| Source          | Data                                  | Update |
| --------------- | ------------------------------------- | ------ |
| Yahoo Finance   | Asset prices, futures contracts       | Daily  |
| FRED            | US Treasury yields, CPI, GDP, VIX     | Daily  |
| ECB Data Portal | Eurozone government bond yield curves | Daily  |

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
├── ui_design.py          # Streamlit dashboard
├── pyproject.toml        # Dependencies
├── tests/                # Unit tests
└── .github/workflows/    # Daily data refresh (GitHub Actions)
```

## Regime Definitions

| Regime         | GDP YoY | CPI YoY | Interpretation                       |
| -------------- | ------- | ------- | ------------------------------------ |
| 🟢 Goldilocks  | > 2%    | < 2%    | Strong growth, low inflation         |
| 🔴 Overheating | > 2%    | ≥ 2.5%  | Strong growth, high inflation        |
| 🟠 Stagflation | ≤ 1%    | ≥ 2.5%  | Weak growth, high inflation          |
| 🔵 Reflation   | > 1%    | < 1.5%  | Moderate growth, very low inflation  |
| 🟣 Deflation   | —       | —       | Catch-all: weak growth/inflation mix |
