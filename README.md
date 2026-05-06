<p align="center">
  <h1 align="center">📊 Cross-Asset Market Regime Monitor</h1>
  <p align="center">
    A Streamlit dashboard that classifies the macroeconomic environment into five regimes and tracks cross-asset performance across equities, fixed income, commodities, and FX.
  </p>
  <p align="center">
    <a href="https://github.com/FredericBANDEIRA/Cross-Asset-Market-Regime-Monitor/actions/workflows/daily_refresh.yml"><img src="https://github.com/FredericBANDEIRA/Cross-Asset-Market-Regime-Monitor/actions/workflows/daily_refresh.yml/badge.svg" alt="Daily Data Refresh"></a>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/streamlit-1.54%2B-FF4B4B" alt="Streamlit">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </p>
</p>

---

## 🧠 What Is This?

Markets behave differently under different macroeconomic conditions. **Equities rally in Goldilocks** (strong growth, low inflation), **gold spikes in Stagflation** (weak growth, high inflation), and **bonds shine in Deflation** (weak everything).

This dashboard answers one question: **What regime are we in right now, and how is each asset class performing?**

It combines GDP and CPI data to classify the economy into five regimes, then overlays that classification onto 22+ assets in real time — giving you a regime-aware, cross-asset view of the markets.

---

## 🖥️ Dashboard Overview

The dashboard is organized into **5 tabs**, each focused on a different aspect of the market:

### 📊 Overview
- **Regime Timeline** — Color-coded bar chart showing regime history (monthly resolution)
- **Correlation Matrix** — Cross-asset daily return correlations for the selected period
- **Performance Heatmap** — Ranked horizontal bar chart of all asset returns
- **Regime Summary Stats** — Annualized average returns per asset under each regime

### 📈 Macro & Rates
- **GDP vs CPI Trends** — Dual-axis chart with rebased growth and inflation indices
- **VIX** — Volatility index with high-volatility zone highlighting
- **Breakeven Inflation** — 10Y nominal minus TIPS yield, with the 2% Fed target reference
- **Credit Spread** — Baa corporate minus 10Y Treasury (stress indicator)
- **Federal Funds Rate** — Current Fed policy rate history
- **Regime Decomposition** — GDP YoY and CPI YoY plotted with classification threshold lines
- **Real Interest Rate** — 10Y nominal yield minus CPI YoY (financial conditions gauge)

### 🏦 Fixed Income
- **Sovereign Yield Curves** — Interactive US Treasury, Eurozone AAA (~Germany), and Eurozone All (~France) curves with historical comparison (current, 3M ago, 1Y ago)
- **10Y–2Y Spread** — Classic yield curve inversion indicator with NBER recession shading
- **Term Premium** — Bar chart showing how each maturity point has shifted vs 1 year ago
- **Real vs Nominal Yields** — 10Y TIPS vs nominal with breakeven gap visualization

### 💹 Equities & Commodities
- **Cumulative Returns** — Rebased performance of selected assets
- **Futures Term Structure** — Contango/backwardation for Gold, Crude Oil, Wheat, Dollar, S&P 500 (8-month forward curve)
- **Rolling Sharpe Ratio** — 1-year rolling risk-adjusted returns with Sharpe = 1 reference line

### 💱 FX
- **G10 FX Performance** — Rebased currency pair chart with period returns table
- **FX Volatility** — 30-day rolling annualized volatility per currency
- **Carry Indicator** — Short-term rate differentials vs USD (who pays you to hold?)
- **DXY Components** — Weighted contribution of each currency to Dollar Index strength
- **Cross Rates Matrix** — Full 10×10 G10 cross-rate table

---

## ⚙️ Regime Classification Model

The regime is determined by where the US economy sits on a **growth × inflation grid**, using Year-over-Year changes in GDP and CPI:

```
                        Low Inflation              High Inflation
                        (CPI YoY < 2.5%)           (CPI YoY ≥ 3%)
                   ┌─────────────────────────┬─────────────────────────┐
  Strong Growth    │                         │                         │
  (GDP YoY > 4%)   │   🟢 GOLDILOCKS          │   🔴 OVERHEATING         │
                   │   Strong growth,         │   Strong growth,         │
                   │   low inflation           │   rising prices          │
                   ├─────────────────────────┼─────────────────────────┤
  Moderate Growth  │                         │                         │
  (GDP YoY 2-4%)   │   🔵 REFLATION            │   🔴 OVERHEATING         │
                   │   Moderate growth,       │   Moderate growth,       │
                   │   low inflation           │   rising prices          │
                   ├─────────────────────────┼─────────────────────────┤
  Weak Growth     │                         │                         │
  (GDP YoY ≤ 2%)   │   🟣 DEFLATION            │   🟠 STAGFLATION         │
                   │   Weak growth,           │   Weak growth,           │
                   │   low inflation           │   high inflation          │
                   └─────────────────────────┴─────────────────────────┘
```

> **Thresholds** are calibrated on actual US GDP/CPI distributions (2004–2025). YoY changes are computed on monthly-resampled data to avoid artifacts from quarterly GDP reporting.

---

## 📡 Data Sources

| Source | Data | Frequency | Method |
|--------|------|-----------|--------|
| **Yahoo Finance** | Asset prices, futures contracts, G10 FX rates | Daily | `yfinance` |
| **FRED** (Federal Reserve) | GDP, CPI, VIX, US Treasury yields, Fed Funds, Baa spread, TIPS, G10 short rates | Daily / Monthly | Public CSV endpoint (no API key required) |
| **ECB Data Portal** | Eurozone AAA & All-rated government bond yield curves | Daily | REST API |

**Data is auto-refreshed daily at 6 AM UTC** via GitHub Actions, which runs the data pipeline and commits updated CSVs back to the repository.

---

## 📦 Assets Tracked (22)

| Asset Class | Instruments |
|-------------|-------------|
| **US Equities** | S&P 500 (SPY), Nasdaq 100 (QQQ), Russell 2000 (IWM) |
| **International Equities** | CAC 40, FTSE 100, DAX, Nikkei 225, MSCI EAFE, MSCI EM |
| **Fixed Income** | US Nominal Bonds (TLT), TIPS (TIP) |
| **Commodities** | Gold, Silver, Crude Oil, Natural Gas, Copper, Wheat |
| **FX (G10 vs USD)** | EUR, GBP, JPY, CHF, AUD, NZD, CAD, NOK, SEK |
| **Other** | Dollar Index (DXY) |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (fast Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/FredericBANDEIRA/Cross-Asset-Market-Regime-Monitor.git
cd Cross-Asset-Market-Regime-Monitor

# Install dependencies
uv sync
```

### Fetch Data

On first run (or to manually refresh), fetch all market data:

```bash
uv run python -m dashboard.data_collection
```

This downloads data from Yahoo Finance, FRED, and the ECB, and writes CSV files to the `data/` directory.

### Launch the Dashboard

```bash
uv run streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

### Run Tests

```bash
uv run pytest tests/ -v
```

---

## 🏗️ Project Structure

```
Cross-Asset-Market-Regime-Monitor/
│
├── app.py                              # Streamlit entrypoint (sidebar, KPIs, tab routing)
│
├── src/dashboard/                      # Main Python package
│   ├── __init__.py
│   ├── config.py                       # All constants: tickers, thresholds, colors, paths
│   ├── core.py                         # Business logic: regime classification, data loading
│   ├── data_collection.py              # Data pipeline: Yahoo, FRED, ECB → CSV
│   └── charts/                         # One module per dashboard tab
│       ├── overview.py                 # Regime timeline, correlation, heatmap, stats
│       ├── macro.py                    # GDP/CPI, VIX, breakeven, credit, Fed Funds
│       ├── fixed_income.py             # Yield curves, spreads, term premium
│       ├── equities.py                 # Cumulative returns, futures, Sharpe
│       └── fx.py                       # FX performance, vol, carry, DXY, cross rates
│
├── data/                               # Generated CSV data files (committed to Git)
│   ├── all_data.csv                    # Cumulative asset returns
│   ├── macro.csv                       # GDP, CPI, VIX levels
│   ├── sovereign_yields.csv            # US Treasury yield curve
│   ├── ecb_yields_eurozone_aaa.csv     # ECB AAA curve (~Germany)
│   ├── ecb_yields_eurozone_all.csv     # ECB All curve (~France)
│   ├── futures_term_structure.csv      # Commodity/index forward curves
│   ├── macro_indicators.csv            # Fed Funds, credit spread, TIPS
│   ├── fx_rates.csv                    # G10 FX spot rates
│   ├── short_rates.csv                 # G10 short-term interest rates
│   └── vix.csv                         # VIX index
│
├── tests/                              # Unit tests
│   ├── test_regime.py                  # Regime classification logic tests
│   └── test_data_collection.py         # Data processing tests
│
├── .github/workflows/
│   └── daily_refresh.yml               # GitHub Actions: daily data refresh (cron 6AM UTC)
│
├── .streamlit/config.toml              # Dark theme configuration
├── .devcontainer/devcontainer.json      # GitHub Codespaces support
├── pyproject.toml                      # Project metadata & dependencies (hatchling)
├── uv.lock                            # Pinned dependency lock file
└── git_routine.txt                     # Git workflow cheatsheet
```

---

## 🔧 Configuration

All configuration is centralized in [`src/dashboard/config.py`](src/dashboard/config.py):

| Setting | Description | Default |
|---------|-------------|---------|
| `GROWTH_HIGH` | GDP YoY threshold for "strong growth" | 4% |
| `GROWTH_LOW` | GDP YoY threshold for "weak growth" | 2% |
| `INFLATION_HIGH` | CPI YoY threshold for "high inflation" | 3% |
| `INFLATION_LOW` | CPI YoY threshold for "moderate inflation" | 2.5% |
| `START_DATE` | Historical data start date | 2000-01-01 |
| `PLOTLY_TEMPLATE` | Chart theme | `plotly_dark` |

---

## ☁️ Deployment

### Streamlit Community Cloud

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select this repo
4. Set `app.py` as the main file
5. Deploy — data files are already committed to the repo

### GitHub Codespaces

Click **Code → Codespaces → New Codespace**. The devcontainer is pre-configured to install dependencies and launch the dashboard automatically.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Make your changes
4. Run tests: `uv run pytest tests/ -v`
5. Commit with a descriptive message (`git commit -m "feat: add recession probability indicator"`)
6. Push and open a Pull Request

---

## 📄 License

This project is open source. See the repository for license details.

---

## 👤 Author

**Frédéric BANDEIRA**

Built as a personal tool for cross-asset macro analysis and regime-aware portfolio monitoring.
