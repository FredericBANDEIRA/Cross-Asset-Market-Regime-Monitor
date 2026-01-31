import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import timedelta
import datetime

# -----------------------------
# 1. Configuration & Styling
# -----------------------------
TITLE = "Cross-Asset Market Regime Monitor"
st.set_page_config(page_title=TITLE, layout="wide")
st.title(TITLE)

# -----------------------------
# 2. Data Loading (Optimized & Robust)
# -----------------------------
@st.cache_data
def load_and_clean_data():
    """Loads all datasets and handles initial cleaning."""
    # 1. Macro Data: Load RAW levels
    macro_raw = pd.read_csv("macro.csv", index_col=0, parse_dates=True)
    macro_raw = macro_raw.apply(pd.to_numeric, errors='coerce').ffill().dropna()
    
    # Create growth index for visualization [cite: 24, 37]
    # Use fillna(0) to prevent numeric warnings during index creation
    macro_idx = (1 + macro_raw.pct_change().fillna(0)).cumprod()
    
    # 2. Asset Data [cite: 10, 15]
    assets = pd.read_csv("all_data.csv", index_col=0, delimiter=';', parse_dates=True).ffill().dropna()
    
    # 3. Volatility [cite: 13]
    vola = pd.read_csv("vix.csv", index_col=0, parse_dates=True).ffill().dropna()
    
    # 4. Yields [cite: 14]
    yields = pd.read_csv("sovereign_yields.csv", index_col=0, parse_dates=True).ffill().dropna()
    
    return macro_raw, macro_idx, assets, vola, yields

# Unpack carefully - ensure order matches return statement
macro_raw, macro_trends, cum_returns, vola, yields_us = load_and_clean_data()

# -----------------------------
# 3. Regime Classification Logic
# -----------------------------
def classify_regime(row):
    """Determines regime based on YoY thresholds[cite: 12, 31]."""
    # map internal FRED codes back to descriptive names
    g = row.get('GDP', 0)
    i = row.get('CPIAUCNS', 0)
    
    if g > 0.02 and i < 0.02:
        return "Goldilocks"
    elif g > 0.02 and i >= 0.025:
        return "Overheating"
    elif g <= 0.01 and i >= 0.025:
        return "Stagflation"
    elif g > 0.01 and i < 0.015:
        return "Reflation"
    else:
        return "Deflation"

# Calculate YoY (12-period) changes for regime classification [cite: 12]
macro_yoy = macro_raw.pct_change(12).dropna()
macro_yoy['Regime'] = macro_yoy.apply(classify_regime, axis=1)

# -----------------------------
# 4. Sidebar Filters
# -----------------------------
with st.sidebar:
    st.header("Global Settings")
    
    selected_assets = st.multiselect(
        "Select Assets for Detailed View", 
        options=cum_returns.columns, 
        default=cum_returns.columns[:3].tolist()
    )
    
    min_date, max_date = cum_returns.index.min(), cum_returns.index.max()
    date_range = st.date_input(
        "Select Date Range", 
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    st.divider()
    st.header("Regime Monitor")
    selected_regime = st.selectbox(
        "Filter Performance by Regime", 
        options=["All"] + sorted(list(macro_yoy['Regime'].unique()))
    )

# Logic to handle both Date Range and Regime Filter
if len(date_range) == 2:
    start_dt, end_dt = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start_dt, end_dt = min_date, max_date

# Final Filtering Logic for Performance Section
if selected_regime != "All":
    regime_dates = macro_yoy[macro_yoy['Regime'] == selected_regime].index
    display_assets = cum_returns.loc[cum_returns.index.isin(regime_dates)]
    st.info(f"Analysis showing performance during historical **{selected_regime}** periods.")
else:
    display_assets = cum_returns.loc[start_dt:end_dt]

# -----------------------------
# 5. Visualizations
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Macroeconomic Trends")
    fig_macro = px.line(macro_trends.loc[start_dt:end_dt], labels={"value": "Growth Index", "index": "Date"})
    st.plotly_chart(fig_macro, use_container_width=True)

with col2:
    st.subheader("Volatility (VIX)")
    fig_vix = px.line(vola.loc[start_dt:end_dt], labels={"value": "Level %", "index": "Date"})
    st.plotly_chart(fig_vix, use_container_width=True)

st.divider()

# Asset Performance Section
st.subheader(f"Asset Class Performance ({selected_regime} View)")
fig_assets = px.line(
    display_assets[selected_assets] if selected_assets else display_assets,
    title="Cumulative Returns (Selected Filtered Period)"
)
st.plotly_chart(fig_assets, use_container_width=True)

# -----------------------------
# 6. Yield Curve Section
# -----------------------------
st.divider()
st.subheader("US Treasury Term Structure")

MATURITY_MAP = {
    'DTB4WK': 1/12, 'DGS3MO': 0.25, 'DGS6MO': 0.5,
    'DGS1': 1, 'DGS2': 2, 'DGS3': 3, 'DGS5': 5, 
    'DGS7': 7, 'DGS10': 10, 'DGS20': 20, 'DGS30': 30
}

curve_date = st.select_slider(
    "Select specific date for Yield Curve analysis:",
    options=yields_us.index.strftime('%Y-%m-%d').tolist(),
    value=yields_us.index[-1].strftime('%Y-%m-%d')
)
ref_date = pd.Timestamp(curve_date)

historical_dates = {
    "Current": ref_date,
    "3 Months Ago": ref_date - timedelta(days=90),
    "1 Year Ago": ref_date - timedelta(days=365)
}

curve_list = []
for label, dt in historical_dates.items():
    if dt in yields_us.index:
        row = yields_us.loc[dt].rename(MATURITY_MAP).reset_index()
        row.columns = ['Maturity', 'Yield']
        row['Period'] = label
        curve_list.append(row)

if curve_list:
    fig_yield = px.line(pd.concat(curve_list), x='Maturity', y='Yield', color='Period', 
                        markers=True, line_shape='spline', title=f"Yield Curve as of {curve_date}")
    st.plotly_chart(fig_yield, use_container_width=True)

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

    fig_heat = px.imshow(padded_returns.reshape(rows, cols), text_auto=".2%", aspect="auto",
                         color_continuous_scale="RdYlGn", color_continuous_midpoint=0)
    fig_heat.update_traces(text=name_matrix, texttemplate="<b>%{text}</b><br>%{z:.2%}")
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.warning("No data available for the selected regime.")