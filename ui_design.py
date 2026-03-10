import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta

from core import (
    GROWTH_HIGH,
    GROWTH_LOW,
    INFLATION_HIGH,
    INFLATION_LOW,
    REGIME_COLORS,
    classify_regime,
    load_and_clean_data as _load_data,
)

# -----------------------------
# 1. Configuration & Styling
# -----------------------------
TITLE = "Cross-Asset Market Regime Monitor"
st.set_page_config(page_title=TITLE, layout="wide")

# Plotly dark theme for all charts
PLOTLY_TEMPLATE = "plotly_dark"

st.title(TITLE)


# -----------------------------
# 2. Data Loading (Cached)
# -----------------------------
@st.cache_data
def load_and_clean_data():
    """Thin Streamlit wrapper — caching around core.load_and_clean_data()."""
    return _load_data()


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
) = load_and_clean_data()


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
        index=9,  # Default to "Max"
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
                [sys.executable, "data_collection.py"],
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
    # Regime Timeline
    st.subheader("Regime Timeline")
    regime_ts = (
        macro_yoy.loc[start_dt:end_dt, "Regime"]
        if selected_regime == "All"
        else macro_yoy["Regime"]
    )
    if not regime_ts.empty:
        # Downsample to monthly for performance (~240 bars vs ~7000 daily)
        regime_monthly = regime_ts.resample("ME").last().dropna()

        fig_regime = go.Figure()
        for regime, color in REGIME_COLORS.items():
            mask = regime_monthly == regime
            if mask.any():
                fig_regime.add_trace(
                    go.Bar(
                        x=regime_monthly.index[mask],
                        y=[1] * mask.sum(),
                        marker_color=color,
                        name=regime,
                        width=86400000 * 31,  # ~1 month in ms
                    )
                )
        fig_regime.update_layout(
            barmode="stack",
            template=PLOTLY_TEMPLATE,
            yaxis=dict(visible=False),
            xaxis_title="",
            height=220,
            margin=dict(l=0, r=0, t=0, b=30),
            legend=dict(orientation="h", y=1.15),
            bargap=0,
        )
        st.plotly_chart(fig_regime, width="stretch")

    # Cross-Asset Correlation Matrix
    corr_cols = [c for c in CORR_ASSETS if c in cum_returns.columns]
    st.subheader("Cross-Asset Correlation Matrix")
    st.caption(
        f"Based on daily returns from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}."
    )
    if corr_cols:
        returns_for_corr = (
            cum_returns.loc[start_dt:end_dt, corr_cols].pct_change().dropna()
        )
        if len(returns_for_corr) > 20:
            corr = returns_for_corr.corr()
            fig_corr = px.imshow(
                corr.round(2),
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="RdBu_r",
                color_continuous_midpoint=0,
                zmin=-1,
                zmax=1,
                template=PLOTLY_TEMPLATE,
            )
            fig_corr.update_layout(height=400)
            st.plotly_chart(fig_corr, width="stretch")
        else:
            st.info("Not enough data points for a meaningful correlation matrix.")
    else:
        st.info("Core assets not available for correlation analysis.")

    # Performance Heatmap — sorted horizontal bar chart
    st.subheader("Asset Performance Heatmap")
    if not display_assets.empty:
        h_start = display_assets.index.min()
        h_end = display_assets.index.max()
        period_returns = (display_assets.loc[h_end] / display_assets.loc[h_start]) - 1
        period_returns = period_returns.sort_values(ascending=True)

        colors = ["#e74c3c" if r < 0 else "#2ecc71" for r in period_returns.values]
        fig_perf = go.Figure(
            go.Bar(
                x=period_returns.values * 100,
                y=period_returns.index,
                orientation="h",
                marker_color=colors,
                text=[f"{r:+.1f}%" for r in period_returns.values * 100],
                textposition="outside",
                textfont=dict(size=12),
            )
        )
        fig_perf.update_layout(
            template=PLOTLY_TEMPLATE,
            height=max(400, len(period_returns) * 32),
            xaxis_title="Return (%)",
            yaxis_title="",
            margin=dict(l=120, r=60),
        )
        fig_perf.add_vline(x=0, line_dash="dash", line_color="white", opacity=0.3)
        st.plotly_chart(fig_perf, width="stretch")
        st.caption(
            "⚠️ Over long periods (e.g. Max), compounding amplifies differences. "
            "Use the sidebar Time Range filter (e.g. 1Y, 3Y) for more comparable performance."
        )
    else:
        st.warning("No data available for the selected regime.")

    # Regime Summary Stats Table
    st.subheader("Regime Summary Statistics")
    st.caption("Average annualized return (%) for each asset class under each regime")
    if not cum_returns.empty and not macro_yoy.empty:
        daily_ret = cum_returns.pct_change().dropna()
        # Align regime labels with returns
        regime_labels = (
            macro_yoy["Regime"].reindex(daily_ret.index, method="ffill").dropna()
        )
        aligned_ret = daily_ret.loc[regime_labels.index]

        regime_stats = (
            aligned_ret.groupby(regime_labels)
            .mean()
            .mul(252 * 100)  # annualize & convert to %
            .round(2)
            .T  # assets as rows, regimes as columns
        )
        # Order regimes logically
        regime_order = [
            r
            for r in [
                "Goldilocks",
                "Reflation",
                "Overheating",
                "Stagflation",
                "Deflation",
            ]
            if r in regime_stats.columns
        ]
        regime_stats = regime_stats[regime_order]

        def _color_returns(val):
            if pd.isna(val):
                return ""
            return f"color: {'#2ecc71' if val > 0 else '#e74c3c'}"

        st.dataframe(
            regime_stats.style.map(_color_returns).format("{:+.2f}%"),
            width=900,
            height=min(600, len(regime_stats) * 36 + 40),
        )
    else:
        st.info("Not enough data to compute regime summary statistics.")

# ═══════════════════════════════════════════════════════
# TAB 2: Macro & Rates
# ═══════════════════════════════════════════════════════
with tab_macro:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Macroeconomic Trends")
        macro_display = macro_trends.loc[start_dt:end_dt].drop(
            columns=["VIXCLS"], errors="ignore"
        )
        if not macro_display.empty:
            macro_display = macro_display / macro_display.iloc[0] * 100  # rebase to 100
        macro_display = macro_display.rename(
            columns={"CPIAUCNS": "Inflation (CPI)", "GDP": "Growth (GDP)"}
        )
        # Dual y-axes so GDP (quarterly) isn't dwarfed by CPI (monthly)
        fig_macro = go.Figure()
        fig_macro.add_trace(
            go.Scatter(
                x=macro_display.index,
                y=macro_display["Inflation (CPI)"],
                name="Inflation (CPI)",
                line=dict(color="#e67e22", width=2),
                yaxis="y",
            )
        )
        fig_macro.add_trace(
            go.Scatter(
                x=macro_display.index,
                y=macro_display["Growth (GDP)"],
                name="Growth (GDP)",
                line=dict(color="#3498db", width=2),
                yaxis="y2",
            )
        )
        fig_macro.update_layout(
            template=PLOTLY_TEMPLATE,
            xaxis_title="",
            yaxis=dict(
                title=dict(text="CPI Index", font=dict(color="#e67e22")), side="left"
            ),
            yaxis2=dict(
                title=dict(text="GDP Index", font=dict(color="#3498db")),
                side="right",
                overlaying="y",
            ),
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig_macro, width="stretch")
        st.caption(
            "Both series rebased to 100 at period start. GDP updates quarterly (stepped), CPI monthly."
        )

    with col2:
        st.subheader("Volatility (VIX)")
        vix_period = vola.loc[start_dt:end_dt]
        fig_vix = px.line(
            vix_period,
            labels={"value": "VIX Index", "variable": ""},
            template=PLOTLY_TEMPLATE,
        )
        fig_vix.update_layout(xaxis_title="", showlegend=False)
        vix_max = float(vix_period.max().max()) if not vix_period.empty else 80
        fig_vix.add_hrect(
            y0=25,
            y1=max(vix_max + 5, 30),
            fillcolor="red",
            opacity=0.08,
            annotation_text="High Vol",
            annotation_position="top left",
        )
        st.plotly_chart(fig_vix, width="stretch")

    # Breakeven Inflation (full width)
    if not indicators.empty:
        if "DFII10" in indicators.columns and "DGS10" in yields_us.columns:
            st.subheader("Breakeven Inflation (10Y)")
            combined = pd.DataFrame(
                {
                    "Nominal 10Y": yields_us["DGS10"],
                    "Real 10Y (TIPS)": indicators["DFII10"],
                }
            ).dropna()
            combined["Breakeven"] = (
                combined["Nominal 10Y"] - combined["Real 10Y (TIPS)"]
            )
            be = combined.loc[start_dt:end_dt, "Breakeven"]
            if not be.empty:
                fig_be = go.Figure()
                fig_be.add_trace(
                    go.Scatter(
                        x=be.index,
                        y=be.values,
                        mode="lines",
                        name="Breakeven Inflation",
                        line=dict(color="#e67e22", width=1.5),
                        fill="tozeroy",
                        fillcolor="rgba(230,126,34,0.1)",
                    )
                )
                fig_be.add_hline(
                    y=2.0,
                    line_dash="dash",
                    line_color="white",
                    opacity=0.5,
                    annotation_text="2% Target",
                )
                fig_be.update_layout(
                    template=PLOTLY_TEMPLATE,
                    height=300,
                    xaxis_title="",
                    yaxis_title="Rate (%)",
                    showlegend=False,
                )
                st.plotly_chart(fig_be, width="stretch")

        # Credit Spread (full width)
        if "BAA10Y" in indicators.columns:
            st.subheader("Credit Spread (Baa – 10Y)")
            cs = indicators.loc[start_dt:end_dt, "BAA10Y"].dropna()
            if not cs.empty:
                fig_cs = go.Figure()
                fig_cs.add_trace(
                    go.Scatter(
                        x=cs.index,
                        y=cs.values,
                        mode="lines",
                        name="Baa – 10Y",
                        line=dict(color="#9b59b6", width=1.5),
                    )
                )
                fig_cs.add_hrect(
                    y0=3.0,
                    y1=cs.max() + 0.5,
                    fillcolor="red",
                    opacity=0.08,
                    annotation_text="Stress",
                    annotation_position="top left",
                )
                fig_cs.update_layout(
                    template=PLOTLY_TEMPLATE,
                    height=300,
                    xaxis_title="",
                    yaxis_title="Spread (%)",
                    showlegend=False,
                )
                st.plotly_chart(fig_cs, width="stretch")

        # Fed Funds Rate (full width)
        if "DFF" in indicators.columns:
            st.subheader("Federal Funds Rate")
            ff = indicators.loc[start_dt:end_dt, "DFF"].dropna()
            if not ff.empty:
                fig_ff = go.Figure()
                fig_ff.add_trace(
                    go.Scatter(
                        x=ff.index,
                        y=ff.values,
                        mode="lines",
                        name="Fed Funds Rate",
                        line=dict(color="#2ecc71", width=1.5),
                        fill="tozeroy",
                        fillcolor="rgba(46,204,113,0.1)",
                    )
                )
                fig_ff.update_layout(
                    template=PLOTLY_TEMPLATE,
                    height=250,
                    xaxis_title="",
                    yaxis_title="Rate (%)",
                    showlegend=False,
                )
                st.plotly_chart(fig_ff, width="stretch")

    # --- Regime Decomposition: GDP vs CPI YoY ---
    st.divider()
    st.subheader("Regime Decomposition — Growth vs Inflation (YoY)")
    decomp = macro_yoy.loc[start_dt:end_dt, ["GDP", "CPIAUCNS"]].copy()
    decomp = decomp * 100  # convert to percentage
    if not decomp.empty:
        dec_col1, dec_col2 = st.columns(2)

        with dec_col1:
            st.subheader("GDP Growth (YoY)")
            fig_gdp = go.Figure()
            fig_gdp.add_trace(
                go.Scatter(
                    x=decomp.index,
                    y=decomp["GDP"],
                    mode="lines",
                    name="GDP YoY",
                    line=dict(color="#3498db", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(52,152,219,0.1)",
                )
            )
            fig_gdp.add_hline(
                y=GROWTH_HIGH * 100,
                line_dash="dot",
                line_color="white",
                opacity=0.5,
                annotation_text=f"High ({GROWTH_HIGH * 100:.0f}%)",
                annotation_position="bottom right",
            )
            fig_gdp.add_hline(
                y=GROWTH_LOW * 100,
                line_dash="dot",
                line_color="white",
                opacity=0.5,
                annotation_text=f"Low ({GROWTH_LOW * 100:.0f}%)",
                annotation_position="bottom right",
            )
            fig_gdp.update_layout(
                template=PLOTLY_TEMPLATE,
                height=300,
                xaxis_title="",
                yaxis_title="GDP YoY (%)",
                showlegend=False,
            )
            st.plotly_chart(fig_gdp, width="stretch")

        with dec_col2:
            st.subheader("CPI Inflation (YoY)")
            fig_cpi = go.Figure()
            fig_cpi.add_trace(
                go.Scatter(
                    x=decomp.index,
                    y=decomp["CPIAUCNS"],
                    mode="lines",
                    name="CPI YoY",
                    line=dict(color="#e74c3c", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(231,76,60,0.1)",
                )
            )
            fig_cpi.add_hline(
                y=INFLATION_HIGH * 100,
                line_dash="dot",
                line_color="white",
                opacity=0.5,
                annotation_text=f"High ({INFLATION_HIGH * 100:.0f}%)",
                annotation_position="top right",
            )
            fig_cpi.add_hline(
                y=INFLATION_LOW * 100,
                line_dash="dot",
                line_color="white",
                opacity=0.5,
                annotation_text=f"Low ({INFLATION_LOW * 100:.1f}%)",
                annotation_position="top right",
            )
            fig_cpi.update_layout(
                template=PLOTLY_TEMPLATE,
                height=300,
                xaxis_title="",
                yaxis_title="CPI YoY (%)",
                showlegend=False,
            )
            st.plotly_chart(fig_cpi, width="stretch")

        st.caption(
            "Dotted lines show the regime classification thresholds. "
            "The combination of growth and inflation determines the current regime."
        )

    # --- Real Rates: 10Y Nominal minus CPI YoY ---
    st.divider()
    st.subheader("Real Interest Rate (10Y Nominal − CPI YoY)")
    if (
        not yields_us.empty
        and "DGS10" in yields_us.columns
        and not macro_yoy.empty
        and "CPIAUCNS" in macro_yoy.columns
    ):
        cpi_yoy_pct = macro_yoy["CPIAUCNS"] * 100  # already in decimal, convert to %
        nominal_10y = yields_us["DGS10"]
        # Align on common dates
        real_rate = (nominal_10y - cpi_yoy_pct).dropna()
        real_rate = real_rate.loc[start_dt:end_dt]
        if not real_rate.empty:
            fig_real = go.Figure()
            fig_real.add_trace(
                go.Scatter(
                    x=real_rate.index,
                    y=real_rate.values,
                    mode="lines",
                    name="Real Rate",
                    line=dict(color="#1abc9c", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(26,188,156,0.1)",
                )
            )
            fig_real.add_hline(
                y=0,
                line_dash="dash",
                line_color="white",
                opacity=0.5,
                annotation_text="0%",
                annotation_position="bottom right",
            )
            fig_real.update_layout(
                template=PLOTLY_TEMPLATE,
                height=300,
                xaxis_title="",
                yaxis_title="Real Rate (%)",
                showlegend=False,
            )
            st.plotly_chart(fig_real, width="stretch")
            st.caption(
                "Real rate = 10Y Treasury yield − CPI YoY%. "
                "Negative real rates signal accommodative conditions; "
                "positive real rates tighten financial conditions."
            )
        else:
            st.info("Not enough overlapping data for real rate calculation.")
    else:
        st.info("Yield or CPI data not available for real rate calculation.")

# ═══════════════════════════════════════════════════════
# TAB 3: Fixed Income
# ═══════════════════════════════════════════════════════
with tab_fi:
    st.subheader("Sovereign Yield Curves")

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

    yield_curves = {"US Treasury": yields_us}
    if not ecb_aaa.empty:
        yield_curves["Eurozone AAA (\u2248 Germany)"] = ecb_aaa
    if not ecb_all.empty:
        yield_curves["Eurozone All (\u2248 France)"] = ecb_all

    selected_country = st.radio(
        "Select Curve", list(yield_curves.keys()), horizontal=True
    )
    curve_data = yield_curves[selected_country]
    curve_data.index = pd.to_datetime(curve_data.index)  # ensure DatetimeIndex

    curve_date = st.select_slider(
        "Select date for Yield Curve analysis:",
        options=curve_data.index.strftime("%Y-%m-%d").tolist(),
        value=curve_data.index[-1].strftime("%Y-%m-%d"),
    )
    ref_date = pd.Timestamp(curve_date)

    historical_dates = {
        "Current": ref_date,
        "3 Months Ago": ref_date - timedelta(days=90),
        "1 Year Ago": ref_date - timedelta(days=365),
    }

    curve_list = []
    for label, dt in historical_dates.items():
        nearest = curve_data.index.asof(dt)
        if pd.notna(nearest):
            if selected_country == "US Treasury":
                row = curve_data.loc[nearest].rename(US_MATURITY_MAP).reset_index()
            else:
                row = curve_data.loc[nearest].reset_index()
            row.columns = ["Maturity", "Yield"]
            row["Maturity"] = pd.to_numeric(row["Maturity"], errors="coerce")
            row["Period"] = label
            curve_list.append(row)

    if curve_list:
        fig_yield = px.line(
            pd.concat(curve_list),
            x="Maturity",
            y="Yield",
            color="Period",
            markers=True,
            line_shape="spline",
            title=f"{selected_country} Yield Curve as of {curve_date}",
            template=PLOTLY_TEMPLATE,
        )
        fig_yield.update_layout(xaxis_title="Maturity (Years)", yaxis_title="Yield (%)")
        st.plotly_chart(fig_yield, width="stretch")

    # 10Y – 2Y Yield Spread
    if (
        not yields_us.empty
        and "DGS10" in yields_us.columns
        and "DGS2" in yields_us.columns
    ):
        spread = yields_us["DGS10"] - yields_us["DGS2"]
        spread = spread.loc[start_dt:end_dt].dropna()
        if not spread.empty:
            st.subheader("US 10Y – 2Y Spread (Inversion Indicator)")
            fig_spread = go.Figure()
            fig_spread.add_trace(
                go.Scatter(
                    x=spread.index,
                    y=spread.values,
                    mode="lines",
                    name="10Y – 2Y",
                    line=dict(color="#3498db", width=1.5),
                )
            )
            fig_spread.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            inverted = spread[spread < 0]
            if not inverted.empty:
                fig_spread.add_trace(
                    go.Scatter(
                        x=inverted.index,
                        y=inverted.values,
                        fill="tozeroy",
                        fillcolor="rgba(231,76,60,0.2)",
                        line=dict(color="#e74c3c", width=1.5),
                        name="Inverted",
                    )
                )
            fig_spread.update_layout(
                template=PLOTLY_TEMPLATE,
                xaxis_title="",
                yaxis_title="Spread (%)",
                height=250,
                legend=dict(orientation="h", y=-0.2),
            )
            # Add NBER recession bars for context
            RECESSIONS = [
                ("2001-03-01", "2001-11-01"),  # Dot-com
                ("2007-12-01", "2009-06-01"),  # Great Financial Crisis
                ("2020-02-01", "2020-04-01"),  # COVID-19
            ]
            for rec_start, rec_end in RECESSIONS:
                fig_spread.add_vrect(
                    x0=rec_start,
                    x1=rec_end,
                    fillcolor="gray",
                    opacity=0.15,
                    line_width=0,
                )
            st.plotly_chart(fig_spread, width="stretch")
            st.caption(
                "Gray shaded areas indicate NBER recession periods. "
                "Yield curve inversion (red) has historically preceded recessions."
            )

    # --- Term Premium Estimate ---
    st.divider()
    st.subheader("Term Premium Estimate (Current vs 1Y Ago Curve)")
    if not yields_us.empty:
        latest_date = yields_us.index[-1]
        one_year_ago = latest_date - timedelta(days=365)
        nearest_1y = yields_us.index.asof(one_year_ago)
        if pd.notna(nearest_1y):
            current_curve = yields_us.loc[latest_date]
            past_curve = yields_us.loc[nearest_1y]
            tp_diff = (current_curve - past_curve).rename(US_MATURITY_MAP)
            tp_diff = tp_diff.sort_index()

            colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in tp_diff.values]
            fig_tp = go.Figure(
                go.Bar(
                    x=[f"{m}Y" if m >= 1 else f"{int(m * 12)}M" for m in tp_diff.index],
                    y=tp_diff.values,
                    marker_color=colors,
                    text=[f"{v:+.2f}" for v in tp_diff.values],
                    textposition="outside",
                )
            )
            fig_tp.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.4)
            fig_tp.update_layout(
                template=PLOTLY_TEMPLATE,
                height=300,
                xaxis_title="Maturity",
                yaxis_title="Yield Change (pp)",
                showlegend=False,
            )
            st.plotly_chart(fig_tp, width="stretch")
            st.caption(
                f"Difference between current yield curve ({latest_date.strftime('%Y-%m-%d')}) "
                f"and 1Y ago ({nearest_1y.strftime('%Y-%m-%d')}). "
                "Positive = yields have risen (term premium widened)."
            )

    # --- Real Yield Curve (TIPS vs Nominal) — promoted as key indicator ---
    st.divider()
    st.subheader("Real vs Nominal Yield (10Y)")
    if (
        not yields_us.empty
        and "DGS10" in yields_us.columns
        and not indicators.empty
        and "DFII10" in indicators.columns
    ):
        real_nominal = pd.DataFrame(
            {
                "Nominal 10Y": yields_us["DGS10"],
                "Real 10Y (TIPS)": indicators["DFII10"],
            }
        ).dropna()
        real_nominal = real_nominal.loc[start_dt:end_dt]
        if not real_nominal.empty:
            fig_rn = go.Figure()
            fig_rn.add_trace(
                go.Scatter(
                    x=real_nominal.index,
                    y=real_nominal["Nominal 10Y"],
                    mode="lines",
                    name="Nominal 10Y",
                    line=dict(color="#3498db", width=2),
                )
            )
            fig_rn.add_trace(
                go.Scatter(
                    x=real_nominal.index,
                    y=real_nominal["Real 10Y (TIPS)"],
                    mode="lines",
                    name="Real 10Y (TIPS)",
                    line=dict(color="#e67e22", width=2),
                )
            )
            # Shade the breakeven gap
            fig_rn.add_trace(
                go.Scatter(
                    x=real_nominal.index,
                    y=real_nominal["Nominal 10Y"],
                    mode="lines",
                    line=dict(width=0),
                    showlegend=False,
                )
            )
            fig_rn.add_trace(
                go.Scatter(
                    x=real_nominal.index,
                    y=real_nominal["Real 10Y (TIPS)"],
                    mode="lines",
                    line=dict(width=0),
                    name="Breakeven Gap",
                    fill="tonexty",
                    fillcolor="rgba(155,89,182,0.15)",
                )
            )
            fig_rn.update_layout(
                template=PLOTLY_TEMPLATE,
                height=350,
                xaxis_title="",
                yaxis_title="Yield (%)",
                legend=dict(orientation="h", y=-0.15),
            )
            st.plotly_chart(fig_rn, width="stretch")
            st.caption(
                "The shaded area represents breakeven inflation "
                "(the gap between nominal and real yields)."
            )

# ═══════════════════════════════════════════════════════
# TAB 4: Equities & Commodities
# ═══════════════════════════════════════════════════════
with tab_eq:
    st.subheader(f"Asset Class Performance ({selected_regime} View)")
    plot_assets = display_assets[selected_assets] if selected_assets else display_assets
    if not plot_assets.empty:
        plot_assets = plot_assets / plot_assets.iloc[0]
    fig_assets = px.line(
        plot_assets,
        title="Cumulative Returns (rebased to 1.0)",
        template=PLOTLY_TEMPLATE,
    )
    fig_assets.update_layout(
        xaxis_title="",
        yaxis_title="Cumulative Return",
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig_assets, width="stretch")

    # Futures Term Structure
    st.divider()
    st.subheader("Futures Term Structures")
    if not futures_ts.empty:
        commodities = sorted(futures_ts["commodity"].unique())
        selected_commodity = st.selectbox("Select Commodity", commodities)

        commodity_data = futures_ts[
            futures_ts["commodity"] == selected_commodity
        ].copy()
        commodity_data["expiry_date"] = pd.to_datetime(commodity_data["expiry_date"])
        commodity_data = commodity_data.sort_values("expiry_date")
        # Filter out stale/zero-price contracts
        commodity_data = commodity_data[commodity_data["price"] > 0]

        fig_term = px.line(
            commodity_data,
            x="expiry",
            y="price",
            title=f"{selected_commodity} — Futures Term Structure",
            markers=True,
            labels={"expiry": "Contract Expiry", "price": "Price ($)"},
            template=PLOTLY_TEMPLATE,
        )
        fig_term.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_term, width="stretch")

        with st.expander("View raw data"):
            st.dataframe(
                commodity_data[["ticker", "expiry", "price"]].reset_index(drop=True)
            )
    else:
        st.info(
            "No futures term structure data available. "
            "Run `python data_collection.py` to fetch it."
        )

    # --- Rolling Sharpe Ratio ---
    st.divider()
    st.subheader("Rolling Sharpe Ratio (1-Year Window)")
    all_sharpe_assets = [
        a
        for a in ["S&P 500", "Nasdaq 100", "Gold", "Nominal Bonds", "Dollar Index"]
        if a in cum_returns.columns
    ]
    if all_sharpe_assets:
        sharpe_selection = st.multiselect(
            "Select assets for Sharpe comparison",
            options=all_sharpe_assets,
            default=all_sharpe_assets[:3],
            key="sharpe_select",
        )
        sharpe_assets = sharpe_selection if sharpe_selection else all_sharpe_assets
        daily_ret_sharpe = cum_returns[sharpe_assets].pct_change().dropna()
        window = 252  # 1 year trading days
        if len(daily_ret_sharpe) > window:
            rolling_mean = daily_ret_sharpe.rolling(window).mean() * 252
            rolling_std = daily_ret_sharpe.rolling(window).std() * np.sqrt(252)
            rolling_sharpe = (rolling_mean / rolling_std).dropna()
            rolling_sharpe = rolling_sharpe.loc[start_dt:end_dt]

            if not rolling_sharpe.empty:
                fig_sharpe = px.line(
                    rolling_sharpe,
                    labels={"value": "Sharpe Ratio", "variable": ""},
                    template=PLOTLY_TEMPLATE,
                )
                fig_sharpe.add_hline(
                    y=0,
                    line_dash="dash",
                    line_color="white",
                    opacity=0.4,
                )
                fig_sharpe.add_hline(
                    y=1.0,
                    line_dash="dot",
                    line_color="#2ecc71",
                    opacity=0.4,
                    annotation_text="Sharpe = 1",
                    annotation_position="bottom right",
                )
                fig_sharpe.update_layout(
                    height=350,
                    xaxis_title="",
                    yaxis_title="Sharpe Ratio",
                    legend=dict(orientation="h", y=-0.15),
                )
                st.plotly_chart(fig_sharpe, width="stretch")
                st.caption(
                    "Rolling 252-day (1Y) annualized Sharpe ratio. "
                    "Values above 1 indicate strong risk-adjusted returns."
                )
        else:
            st.info("Not enough data for a 1-year rolling Sharpe calculation.")
    else:
        st.info("Key assets not available for Sharpe calculation.")

# ═══════════════════════════════════════════════════════
# TAB 5: FX
# ═══════════════════════════════════════════════════════
with tab_fx:
    if not fx_rates.empty:
        # --- FX Performance Chart + Period Returns Table ---
        st.subheader("G10 FX Performance (Rebased to 1.0)")
        fx_period = fx_rates.loc[start_dt:end_dt]
        if not fx_period.empty and len(fx_period) > 1:
            # Period returns summary table
            fx_pct = ((fx_period.iloc[-1] / fx_period.iloc[0]) - 1) * 100
            fx_pct = fx_pct.sort_values(ascending=False)
            fx_summary = pd.DataFrame(
                {
                    "Currency": fx_pct.index,
                    "Period Return (%)": [f"{v:+.2f}%" for v in fx_pct.values],
                }
            ).reset_index(drop=True)
            st.dataframe(
                fx_summary,
                width="stretch",
                height=min(350, len(fx_summary) * 35 + 40),
            )

            fx_rebased = fx_period / fx_period.iloc[0]
            fig_fx_perf = px.line(
                fx_rebased,
                labels={"value": "Relative Value", "variable": "Currency"},
                template=PLOTLY_TEMPLATE,
            )
            fig_fx_perf.add_hline(
                y=1.0,
                line_dash="dash",
                line_color="white",
                opacity=0.3,
            )
            fig_fx_perf.update_layout(
                height=400,
                xaxis_title="",
                yaxis_title="Relative to Start",
                legend=dict(orientation="h", y=-0.15),
            )
            st.plotly_chart(fig_fx_perf, width="stretch")
            st.caption(
                "Each G10 currency pair rebased to 1.0 at the start of the selected period. "
                "Values above 1.0 indicate appreciation vs USD (or USD depreciation for USD-base pairs)."
            )

        # --- FX Volatility ---
        st.divider()
        st.subheader("FX Volatility (30-Day Rolling Std)")
        fx_daily_ret = fx_rates.pct_change().dropna()
        fx_vol = (
            fx_daily_ret.rolling(30).std().dropna() * np.sqrt(252) * 100
        )  # annualized %
        fx_vol_period = fx_vol.loc[start_dt:end_dt]
        if not fx_vol_period.empty:
            vol_currencies = st.multiselect(
                "Select currencies for volatility comparison",
                options=fx_vol_period.columns.tolist(),
                default=fx_vol_period.columns[:4].tolist(),
                key="fx_vol_select",
            )
            vol_display = (
                fx_vol_period[vol_currencies] if vol_currencies else fx_vol_period
            )
            fig_fx_vol = px.line(
                vol_display,
                labels={"value": "Annualized Vol (%)", "variable": "Currency"},
                template=PLOTLY_TEMPLATE,
            )
            fig_fx_vol.update_layout(
                height=350,
                xaxis_title="",
                yaxis_title="Annualized Volatility (%)",
                legend=dict(orientation="h", y=-0.15),
            )
            st.plotly_chart(fig_fx_vol, width="stretch")
            st.caption(
                "30-day rolling standard deviation of daily returns, annualized. "
                "Higher readings indicate larger currency moves."
            )

        # --- Carry Indicator ---
        st.divider()
        st.subheader("Carry Indicator (Rate Differentials vs USD)")
        if not short_rates.empty and "USD" in short_rates.columns:
            latest_rates = short_rates.dropna(how="all").iloc[-1]
            usd_rate = latest_rates.get("USD", np.nan)
            if pd.notna(usd_rate):
                diffs = {}
                for ccy in latest_rates.index:
                    if ccy != "USD" and pd.notna(latest_rates[ccy]):
                        diffs[ccy] = latest_rates[ccy] - usd_rate
                if diffs:
                    carry_df = pd.Series(diffs).sort_values(ascending=True)
                    colors_carry = [
                        "#e74c3c" if v < 0 else "#2ecc71" for v in carry_df.values
                    ]
                    fig_carry = go.Figure(
                        go.Bar(
                            x=carry_df.values,
                            y=carry_df.index,
                            orientation="h",
                            marker_color=colors_carry,
                            text=[f"{v:+.2f}%" for v in carry_df.values],
                            textposition="outside",
                        )
                    )
                    fig_carry.add_vline(
                        x=0, line_dash="dash", line_color="white", opacity=0.4
                    )
                    fig_carry.update_layout(
                        template=PLOTLY_TEMPLATE,
                        height=350,
                        xaxis_title="Rate Differential vs USD (%)",
                        yaxis_title="",
                        showlegend=False,
                    )
                    st.plotly_chart(fig_carry, width="stretch")
                    st.caption(
                        f"Short-term interest rate minus US Fed Funds Rate ({usd_rate:.2f}%). "
                        "Positive = higher carry in foreign currency. "
                        f"Data as of {short_rates.dropna(how='all').index[-1].strftime('%Y-%m-%d')}."
                    )
                else:
                    st.info("No foreign rate data available for carry calculation.")
            else:
                st.info("USD rate not available for carry calculation.")
        else:
            st.info(
                "Short-term rate data not available. "
                "Run `python data_collection.py` to fetch carry indicator data."
            )

        # --- DXY Components ---
        st.divider()
        st.subheader("DXY Components — Currency Contribution to Dollar Strength")
        # Official ICE DXY weights
        DXY_WEIGHTS = {
            "EUR": 0.576,
            "JPY": 0.136,
            "GBP": 0.119,
            "CAD": 0.091,
            "SEK": 0.042,
            "CHF": 0.036,
        }
        # For USD-quote pairs (EUR, GBP), a rise = USD weakens
        # For USD-base pairs (JPY, CAD, SEK, CHF), a rise = USD strengthens
        usd_quote_set = {"EUR", "GBP"}
        dxy_ccys = [c for c in DXY_WEIGHTS if c in fx_rates.columns]
        if dxy_ccys:
            fx_period_dxy = fx_rates[dxy_ccys].loc[start_dt:end_dt]
            if len(fx_period_dxy) > 1:
                pct_change_total = (
                    fx_period_dxy.iloc[-1] / fx_period_dxy.iloc[0] - 1
                ) * 100
                contributions = {}
                for ccy in dxy_ccys:
                    w = DXY_WEIGHTS[ccy]
                    chg = pct_change_total[ccy]
                    # For USD-quote pairs, USD strengthens when pair falls
                    if ccy in usd_quote_set:
                        contributions[ccy] = -chg * w  # invert: pair down = USD up
                    else:
                        contributions[ccy] = chg * w  # pair up = USD up

                contrib_s = pd.Series(contributions).sort_values()
                colors_dxy = [
                    "#e74c3c" if v < 0 else "#2ecc71" for v in contrib_s.values
                ]
                fig_dxy = go.Figure(
                    go.Bar(
                        x=contrib_s.values,
                        y=[
                            f"{c} ({DXY_WEIGHTS[c] * 100:.1f}%)"
                            for c in contrib_s.index
                        ],
                        orientation="h",
                        marker_color=colors_dxy,
                        text=[f"{v:+.2f}%" for v in contrib_s.values],
                        textposition="outside",
                    )
                )
                total_dxy_chg = sum(contributions.values())
                fig_dxy.add_vline(
                    x=0, line_dash="dash", line_color="white", opacity=0.4
                )
                fig_dxy.update_layout(
                    template=PLOTLY_TEMPLATE,
                    height=300,
                    xaxis_title="Contribution to DXY Move (%)",
                    yaxis_title="",
                    showlegend=False,
                    title=f"Estimated DXY Contribution ({total_dxy_chg:+.2f}% total)",
                )
                st.plotly_chart(fig_dxy, width="stretch")
                st.caption(
                    "Weighted contribution of each currency to the Dollar Index (DXY) move. "
                    "Green = strengthens USD, Red = weakens USD. "
                    "Weights in parentheses are the official ICE DXY basket weights."
                )

        # --- Cross Rates Matrix ---
        st.divider()
        st.subheader("G10 FX Cross Rates")
        latest_fx = fx_rates.iloc[-1].to_dict()

        usd_quote = {"EUR", "GBP", "AUD", "NZD"}
        usd_base = {"JPY", "CHF", "CAD", "NOK", "SEK"}

        usd_per_unit = {"USD": 1.0}
        for ccy, rate in latest_fx.items():
            if ccy in usd_quote:
                usd_per_unit[ccy] = rate
            elif ccy in usd_base:
                usd_per_unit[ccy] = 1.0 / rate

        currencies = list(usd_per_unit.keys())
        cross_matrix = pd.DataFrame(index=currencies, columns=currencies, dtype=float)

        for base in currencies:
            for quote in currencies:
                cross_matrix.loc[base, quote] = usd_per_unit[base] / usd_per_unit[quote]

        cross_matrix = cross_matrix.astype(float).round(4)

        def _color_cross_rates(val):
            if pd.isna(val):
                return ""
            if abs(val - 1.0) < 0.001:  # diagonal (identity)
                return "font-weight: bold; background-color: rgba(255,255,255,0.1)"
            return ""

        st.dataframe(
            cross_matrix.style.map(_color_cross_rates).format("{:.4f}"),
            width="stretch",
            height=400,
        )
        st.caption(
            f"Base currency (rows) \u2192 Quote currency (columns) "
            f"| Rates as of {fx_rates.index[-1].strftime('%Y-%m-%d')} "
            f"| Source: Yahoo Finance"
        )
    else:
        st.info("No FX data available. Run `python data_collection.py` to fetch it.")
