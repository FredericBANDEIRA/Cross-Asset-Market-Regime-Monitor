import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dashboard.config import REGIME_COLORS, PLOTLY_TEMPLATE, CORR_ASSETS


def render(*, cum_returns, macro_yoy, display_assets, start_dt, end_dt, selected_regime):
    """Render the Overview tab contents."""
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
