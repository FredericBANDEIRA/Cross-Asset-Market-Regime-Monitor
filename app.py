import streamlit as st
import pandas as pd
from datetime import timedelta

from dashboard.config import REGIME_COLORS
from dashboard.core import classify_regime, load_and_clean_data
from dashboard.charts import overview, macro, fixed_income, equities, fx

# -----------------------------
# 1. Configuration & Styling
# -----------------------------
TITLE = "Cross-Asset Market Regime Monitor"
st.set_page_config(page_title=TITLE, layout="wide")

st.title(TITLE)


# -----------------------------
# 2. Data Loading (Cached)
# -----------------------------
@st.cache_data
def load_data():
    """Thin Streamlit wrapper — caching around core.load_and_clean_data()."""
    return load_and_clean_data()


# Unpack carefully - ensure order matches return statement
(
    macro_raw,
    macro_trends,
    cum_returns,
    vola,
    yields_us,
    ecb_aaa,
    ecb_all,
    futures_ts,
    indicators,
    fx_rates,
    short_rates,
) = load_data()

# Guard: stop early if asset data is missing
if cum_returns.empty:
    st.error(
        "⚠️ **No asset data loaded.** `data/all_data.csv` is empty.\n\n"
        "Run `uv run python -m dashboard.data_collection` to fetch data, then reload."
    )
    st.stop()

# Calculate YoY on MONTHLY-resampled data (GDP is quarterly, CPI monthly)
# pct_change(12) on daily data with ffill produces mostly zeros
macro_monthly = macro_raw.resample("ME").last()
macro_yoy = macro_monthly.pct_change(12).dropna()
macro_yoy["Regime"] = macro_yoy.apply(classify_regime, axis=1)
# Reindex to daily for timeline display (forward-fill monthly regimes)
macro_yoy = macro_yoy.reindex(macro_raw.index, method="ffill").dropna()

# -----------------------------
# 4. Sidebar Filters
# -----------------------------
with st.sidebar:
    st.header("Global Settings")

    selected_assets = st.multiselect(
        "Select Assets for Detailed View",
        options=cum_returns.columns,
        default=cum_returns.columns[:3].tolist(),
    )

    min_date, max_date = cum_returns.index.min(), cum_returns.index.max()

    time_range = st.selectbox(
        "Time Range",
        options=[
            "Past Week",
            "Past Month",
            "Past 3 months",
            "Past 6 months",
            "YTD",
            "1Y",
            "3Y",
            "5Y",
            "10Y",
            "Max",
            "Custom",
        ],
        index=5,  # Default to "Max"
    )

    # Calculate start date from preset
    if time_range == "Past Week":
        preset_start = max_date - timedelta(days=7)
    elif time_range == "Past Month":
        preset_start = max_date - timedelta(days=30)
    elif time_range == "Past 3 months":
        preset_start = max_date - timedelta(days=90)
    elif time_range == "Past 6 months":
        preset_start = max_date - timedelta(days=180)
    elif time_range == "YTD":
        preset_start = pd.Timestamp(f"{max_date.year}-01-01")
    elif time_range == "1Y":
        preset_start = max_date - timedelta(days=365)
    elif time_range == "3Y":
        preset_start = max_date - timedelta(days=3 * 365)
    elif time_range == "5Y":
        preset_start = max_date - timedelta(days=5 * 365)
    elif time_range == "10Y":
        preset_start = max_date - timedelta(days=10 * 365)
    elif time_range == "Max":
        preset_start = min_date
    else:
        preset_start = None  # Custom — use slider below

    if time_range == "Custom":
        date_range = st.slider(
            "Date Range",
            min_value=min_date.to_pydatetime(),
            max_value=max_date.to_pydatetime(),
            value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
            format="YYYY-MM-DD",
        )
        start_dt = pd.to_datetime(date_range[0])
        end_dt = pd.to_datetime(date_range[1])
    else:
        start_dt = max(preset_start, min_date)
        end_dt = max_date

    st.divider()
    st.header("Regime Monitor")
    selected_regime = st.selectbox(
        "Filter Performance by Regime",
        options=["All"] + sorted(list(macro_yoy["Regime"].unique())),
    )

    # --- Data Freshness Indicator ---
    st.divider()
    st.header("Data Status")
    latest_data_date = cum_returns.index[-1] if not cum_returns.empty else None
    if latest_data_date:
        # Use business days to avoid false "stale" warnings on weekends
        bdays = len(pd.bdate_range(latest_data_date, pd.Timestamp.now())) - 1
        if bdays <= 1:
            st.success(f"✅ Data is current ({latest_data_date.strftime('%Y-%m-%d')})")
        elif bdays <= 2:
            st.warning(
                f"⚠️ Data is {bdays} business days old ({latest_data_date.strftime('%Y-%m-%d')})"
            )
        else:
            st.error(
                f"🔴 Data is {bdays} business days stale ({latest_data_date.strftime('%Y-%m-%d')})"
            )
    else:
        st.error("No data loaded.")
        bdays = 999  # Force refresh

    # --- Refresh Button ---
    if st.button("🔄 Refresh Data Now"):
        import subprocess
        import sys

        with st.spinner("Fetching latest market data..."):
            result = subprocess.run(
                [sys.executable, "-m", "dashboard.data_collection"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        if result.returncode == 0:
            st.success("Data refreshed!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"Refresh failed: {result.stderr[-200:]}")

    # --- Export Button ---
    st.divider()
    st.header("Export")
    if not cum_returns.empty:
        export_data = cum_returns.loc[start_dt:end_dt]
        csv_export = export_data.to_csv()
        st.download_button(
            label="📥 Download Returns (CSV)",
            data=csv_export,
            file_name=f"returns_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    # --- Footer ---
    st.divider()
    st.caption("v1.0 · Cross-Asset Market Regime Monitor")

# Final Filtering Logic for Performance Section
if selected_regime != "All":
    regime_dates = macro_yoy[macro_yoy["Regime"] == selected_regime].index
    display_assets = cum_returns.loc[cum_returns.index.isin(regime_dates)]
else:
    display_assets = cum_returns.loc[start_dt:end_dt]

# -----------------------------
# 5. KPI Cards & Regime Badge
# -----------------------------
current_regime = macro_yoy["Regime"].iloc[-1] if not macro_yoy.empty else "Unknown"
regime_color = REGIME_COLORS.get(current_regime, "#95a5a6")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.markdown(
        f'<div style="background:{regime_color};padding:16px;border-radius:10px;text-align:center;">'
        f'<span style="font-size:14px;color:white;">Current Regime</span><br>'
        f'<span style="font-size:28px;font-weight:bold;color:white;">{current_regime}</span></div>',
        unsafe_allow_html=True,
    )

with kpi2:
    vix_latest = float(vola.iloc[-1, 0]) if not vola.empty else 0
    vix_prev = float(vola.iloc[-2, 0]) if len(vola) > 1 else vix_latest
    vix_delta = vix_latest - vix_prev
    vix_label = (
        "🔴 High" if vix_latest > 25 else "🟢 Low" if vix_latest < 15 else "🟡 Moderate"
    )
    st.metric(
        label=f"VIX ({vix_label})",
        value=f"{vix_latest:.1f}",
        delta=f"{vix_delta:+.1f}",
        delta_color="inverse",  # VIX rising = bad → show red
    )

with kpi3:
    if not yields_us.empty and "DGS10" in yields_us.columns:
        us10y = float(yields_us["DGS10"].dropna().iloc[-1])
        us10y_prev = (
            float(yields_us["DGS10"].dropna().iloc[-2])
            if len(yields_us["DGS10"].dropna()) > 1
            else us10y
        )
        us10y_delta = us10y - us10y_prev
        st.metric(
            label="US 10Y Yield",
            value=f"{us10y:.2f}%",
            delta=f"{us10y_delta:+.2f}%",
        )
    else:
        st.metric(label="US 10Y Yield", value="N/A")

with kpi4:
    if not cum_returns.empty and "S&P 500" in cum_returns.columns:
        spy_return = (
            (cum_returns["S&P 500"].iloc[-1] / cum_returns["S&P 500"].iloc[-30] - 1)
            * 100
            if len(cum_returns) > 30
            else 0
        )
        spy_daily = (
            (cum_returns["S&P 500"].iloc[-1] / cum_returns["S&P 500"].iloc[-2] - 1)
            * 100
            if len(cum_returns) > 1
            else 0
        )
        st.metric(
            label="30d S&P 500",
            value=f"{spy_return:+.1f}%",
            delta=f"{spy_daily:+.2f}% today",
        )

with kpi5:
    data_date = (
        cum_returns.index[-1].strftime("%Y-%m-%d") if not cum_returns.empty else "N/A"
    )
    st.metric(label="📅 Data as of", value=data_date)

if selected_regime != "All":
    st.info(f"Showing performance during historical **{selected_regime}** periods.")

# -----------------------------
# 6. Tabbed Visualizations
# -----------------------------

st.divider()
tab_overview, tab_macro, tab_fi, tab_eq, tab_fx = st.tabs(
    [
        "📊 Overview",
        "📈 Macro & Rates",
        "🏦 Fixed Income",
        "💹 Equities & Commodities",
        "💱 FX",
    ]
)

# ═══════════════════════════════════════════════════════
# TAB 1: Overview
# ═══════════════════════════════════════════════════════
with tab_overview:
    overview.render(
        cum_returns=cum_returns,
        macro_yoy=macro_yoy,
        display_assets=display_assets,
        start_dt=start_dt,
        end_dt=end_dt,
        selected_regime=selected_regime
    )

# ═══════════════════════════════════════════════════════
# TAB 2: Macro & Rates
# ═══════════════════════════════════════════════════════
with tab_macro:
    macro.render(
        macro_trends=macro_trends,
        vola=vola,
        indicators=indicators,
        yields_us=yields_us,
        macro_yoy=macro_yoy,
        start_dt=start_dt,
        end_dt=end_dt
    )

# ═══════════════════════════════════════════════════════
# TAB 3: Fixed Income
# ═══════════════════════════════════════════════════════
with tab_fi:
    fixed_income.render(
        yields_us=yields_us,
        ecb_aaa=ecb_aaa,
        ecb_all=ecb_all,
        indicators=indicators,
        start_dt=start_dt,
        end_dt=end_dt
    )

# ═══════════════════════════════════════════════════════
# TAB 4: Equities & Commodities
# ═══════════════════════════════════════════════════════
with tab_eq:
    equities.render(
        display_assets=display_assets,
        selected_assets=selected_assets,
        selected_regime=selected_regime,
        futures_ts=futures_ts,
        cum_returns=cum_returns,
        start_dt=start_dt,
        end_dt=end_dt
    )

# ═══════════════════════════════════════════════════════
# TAB 5: FX
# ═══════════════════════════════════════════════════════
with tab_fx:
    fx.render(
        fx_rates=fx_rates,
        short_rates=short_rates,
        start_dt=start_dt,
        end_dt=end_dt
    )
