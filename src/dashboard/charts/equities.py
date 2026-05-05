import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from dashboard.config import PLOTLY_TEMPLATE


def render(*, display_assets, selected_assets, selected_regime, futures_ts, cum_returns, start_dt, end_dt):
    """Render the Equities & Commodities tab contents."""
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
            "Run data collection to fetch it."
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
