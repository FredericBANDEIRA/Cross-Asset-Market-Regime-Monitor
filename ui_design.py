import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta
import os

# -----------------------------
# 1. Configuration & Styling
# -----------------------------
TITLE = "Cross-Asset Market Regime Monitor"
st.set_page_config(page_title=TITLE, layout="wide")

# Plotly dark theme for all charts
PLOTLY_TEMPLATE = "plotly_dark"

# Regime classification thresholds (YoY rates)
GROWTH_HIGH = 0.02  # GDP YoY above this = strong growth
GROWTH_LOW = 0.01  # GDP YoY below this = weak growth
INFLATION_HIGH = 0.025  # CPI YoY above this = high inflation
INFLATION_LOW = 0.02  # CPI YoY below this = low inflation
INFLATION_VERY_LOW = 0.015  # CPI YoY below this = very low inflation

# Regime color palette
REGIME_COLORS = {
    "Goldilocks": "#2ecc71",  # green
    "Overheating": "#e74c3c",  # red
    "Stagflation": "#e67e22",  # orange
    "Reflation": "#3498db",  # blue
    "Deflation": "#9b59b6",  # purple
}

st.title(TITLE)


# -----------------------------
# 2. Data Loading (Optimized & Robust)
# -----------------------------
@st.cache_data
def load_and_clean_data():
    """Loads all datasets and handles initial cleaning."""
    # 1. Macro Data: Load RAW levels
    macro_raw = pd.read_csv("macro.csv", index_col=0, parse_dates=True)
    macro_raw = macro_raw.apply(pd.to_numeric, errors="coerce").ffill().dropna()

    # Create growth index for visualization [cite: 24, 37]
    # Use fillna(0) to prevent numeric warnings during index creation
    macro_idx = (1 + macro_raw.pct_change().fillna(0)).cumprod()

    # 2. Asset Data [cite: 10, 15]
    assets = (
        pd.read_csv("all_data.csv", index_col=0, delimiter=";", parse_dates=True)
        .ffill()
        .dropna()
    )

    # 3. Volatility [cite: 13]
    vola = pd.read_csv("vix.csv", index_col=0, parse_dates=True).ffill().dropna()

    # 4. US Yields [cite: 14]
    yields_us = (
        pd.read_csv("sovereign_yields.csv", index_col=0, parse_dates=True)
        .ffill()
        .dropna()
    )

    # 5. ECB Yield Curves (optional — files may not exist yet)
    ecb_aaa = pd.DataFrame()
    ecb_all = pd.DataFrame()
    if os.path.exists("ecb_yields_eurozone_aaa.csv"):
        ecb_aaa = pd.read_csv(
            "ecb_yields_eurozone_aaa.csv", index_col=0, parse_dates=True
        )
    if os.path.exists("ecb_yields_eurozone_all.csv"):
        ecb_all = pd.read_csv(
            "ecb_yields_eurozone_all.csv", index_col=0, parse_dates=True
        )

    # 6. Futures Term Structure (optional)
    if os.path.exists("futures_term_structure.csv"):
        futures_ts = pd.read_csv("futures_term_structure.csv")
    else:
        futures_ts = pd.DataFrame()

    return macro_raw, macro_idx, assets, vola, yields_us, ecb_aaa, ecb_all, futures_ts


# Unpack carefully - ensure order matches return statement
macro_raw, macro_trends, cum_returns, vola, yields_us, ecb_aaa, ecb_all, futures_ts = (
    load_and_clean_data()
)


# -----------------------------
# 3. Regime Classification Logic
# -----------------------------
def classify_regime(row):
    """Determines regime based on YoY thresholds."""
    g = row.get("GDP", 0)
    i = row.get("CPIAUCNS", 0)

    if g > GROWTH_HIGH and i < INFLATION_LOW:
        return "Goldilocks"
    elif g > GROWTH_HIGH and i >= INFLATION_HIGH:
        return "Overheating"
    elif g <= GROWTH_LOW and i >= INFLATION_HIGH:
        return "Stagflation"
    elif g > GROWTH_LOW and i < INFLATION_VERY_LOW:
        return "Reflation"
    else:
        return "Deflation"


# Calculate YoY (12-period) changes for regime classification [cite: 12]
macro_yoy = macro_raw.pct_change(12).dropna()
macro_yoy["Regime"] = macro_yoy.apply(classify_regime, axis=1)

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

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(
        f'<div style="background:{regime_color};padding:16px;border-radius:10px;text-align:center;">'
        f'<span style="font-size:14px;color:white;">Current Regime</span><br>'
        f'<span style="font-size:28px;font-weight:bold;color:white;">{current_regime}</span></div>',
        unsafe_allow_html=True,
    )

with kpi2:
    vix_latest = float(vola.iloc[-1, 0]) if not vola.empty else 0
    vix_color = (
        "#e74c3c" if vix_latest > 25 else "#2ecc71" if vix_latest < 15 else "#f39c12"
    )
    st.metric(label="VIX (Latest)", value=f"{vix_latest:.1f}", delta=None)

with kpi3:
    if not yields_us.empty and "DGS10" in yields_us.columns:
        us10y = float(yields_us["DGS10"].iloc[-1])
        st.metric(label="US 10Y Yield", value=f"{us10y:.2f}%")
    else:
        st.metric(label="US 10Y Yield", value="N/A")

with kpi4:
    if not cum_returns.empty:
        spy_return = (
            (cum_returns.iloc[-1, 0] / cum_returns.iloc[-30, 0] - 1) * 100
            if len(cum_returns) > 30
            else 0
        )
        st.metric(label="30d Equities", value=f"{spy_return:+.1f}%")

if selected_regime != "All":
    st.info(f"Showing performance during historical **{selected_regime}** periods.")

# -----------------------------
# 6. Visualizations
# -----------------------------
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Macroeconomic Trends")
    macro_display = macro_trends.loc[start_dt:end_dt].drop(
        columns=["VIXCLS"], errors="ignore"
    )
    # Rebase to 1.0 at start of selected period
    if not macro_display.empty:
        macro_display = macro_display / macro_display.iloc[0]
    macro_display = macro_display.rename(
        columns={"CPIAUCNS": "Inflation (CPI)", "GDP": "Growth (GDP)"}
    )
    # GDP is quarterly → flat steps between quarters. Interpolate for smooth line.
    gdp = macro_display["Growth (GDP)"].copy()
    gdp[gdp.diff().eq(0)] = np.nan
    macro_display["Growth (GDP)"] = gdp.interpolate(method="linear")
    fig_macro = px.line(
        macro_display,
        labels={"value": "Growth Index", "variable": ""},
        template=PLOTLY_TEMPLATE,
    )
    fig_macro.update_layout(xaxis_title="", legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig_macro, width="stretch")

with col2:
    st.subheader("Volatility (VIX)")
    fig_vix = px.line(
        vola.loc[start_dt:end_dt],
        labels={"value": "VIX Index", "variable": ""},
        template=PLOTLY_TEMPLATE,
    )
    fig_vix.update_layout(xaxis_title="", showlegend=False)
    # Add danger zone shading
    fig_vix.add_hrect(
        y0=25,
        y1=vola.max().max() + 5,
        fillcolor="red",
        opacity=0.08,
        annotation_text="High Vol",
        annotation_position="top left",
    )
    st.plotly_chart(fig_vix, width="stretch")

# -----------------------------
# 6a. Regime Timeline
# -----------------------------
st.subheader("Regime Timeline")
regime_ts = (
    macro_yoy.loc[start_dt:end_dt, "Regime"]
    if selected_regime == "All"
    else macro_yoy["Regime"]
)

if not regime_ts.empty:
    # Build one bar per regime block for efficiency
    fig_regime = go.Figure()
    for regime, color in REGIME_COLORS.items():
        mask = regime_ts == regime
        if mask.any():
            fig_regime.add_trace(
                go.Bar(
                    x=regime_ts.index[mask],
                    y=[1] * mask.sum(),
                    marker_color=color,
                    name=regime,
                    width=86400000 * 2,  # 2 days in ms
                )
            )
    fig_regime.update_layout(
        barmode="stack",
        template=PLOTLY_TEMPLATE,
        yaxis=dict(visible=False),
        xaxis_title="",
        height=120,
        margin=dict(l=0, r=0, t=0, b=30),
        legend=dict(orientation="h", y=1.15),
        bargap=0,
    )
    st.plotly_chart(fig_regime, width="stretch")

st.divider()

# Asset Performance Section
st.subheader(f"Asset Class Performance ({selected_regime} View)")
# Rebase to 1.0 at start of selected period
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

# -----------------------------
# 6. Yield Curve Section
# -----------------------------
st.divider()
st.subheader("Sovereign Yield Curves")

# Country selector
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

selected_country = st.radio("Select Curve", list(yield_curves.keys()), horizontal=True)

curve_data = yield_curves[selected_country]

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
            # ECB data: columns are already numeric (years)
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

# 10Y – 2Y Yield Spread (inversion indicator)
if not yields_us.empty and "DGS10" in yields_us.columns and "DGS2" in yields_us.columns:
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
        # Zero line + inversion shading
        fig_spread.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
        # Shade inverted periods
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
        st.plotly_chart(fig_spread, width="stretch")

# -----------------------------
# 6.5 Futures Term Structure Section
# -----------------------------
st.divider()
st.subheader("Futures Term Structures")

if not futures_ts.empty:
    commodities = sorted(futures_ts["commodity"].unique())
    selected_commodity = st.selectbox("Select Commodity", commodities)

    commodity_data = futures_ts[futures_ts["commodity"] == selected_commodity].copy()
    commodity_data["expiry_date"] = pd.to_datetime(commodity_data["expiry_date"])
    commodity_data = commodity_data.sort_values("expiry_date")

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

    # Show data table
    with st.expander("View raw data"):
        st.dataframe(
            commodity_data[["ticker", "expiry", "price"]].reset_index(drop=True)
        )
else:
    st.info(
        "No futures term structure data available. Run `python data_collection.py` to fetch it."
    )

# -----------------------------
# 7. Performance Heatmap
# -----------------------------
st.divider()
st.subheader("Asset Performance Heatmap")

# Calculate returns specifically for the display_assets (regime-aware)
if not display_assets.empty:
    h_start, h_end = display_assets.index.min(), display_assets.index.max()
    period_returns = (display_assets.loc[h_end] / display_assets.loc[h_start]) - 1
    period_returns = period_returns.round(4)

    n_assets = len(period_returns)
    rows = 2
    cols = int(np.ceil(n_assets / rows))
    padded_returns = np.zeros(rows * cols)
    padded_returns[:n_assets] = period_returns.values

    asset_names = list(period_returns.index) + [""] * (rows * cols - n_assets)
    name_matrix = np.array(asset_names).reshape(rows, cols)

    fig_heat = px.imshow(
        padded_returns.reshape(rows, cols),
        text_auto=".2%",
        aspect="auto",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        template=PLOTLY_TEMPLATE,
    )
    fig_heat.update_traces(text=name_matrix, texttemplate="<b>%{text}</b><br>%{z:.2%}")
    st.plotly_chart(fig_heat, width="stretch")
else:
    st.warning("No data available for the selected regime.")
