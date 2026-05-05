import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dashboard.config import PLOTLY_TEMPLATE, DXY_WEIGHTS


def render(*, fx_rates, short_rates, start_dt, end_dt):
    """Render the FX tab contents."""
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
                "Run data collection to fetch carry indicator data."
            )

        # --- DXY Components ---
        st.divider()
        st.subheader("DXY Components — Currency Contribution to Dollar Strength")
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
        st.info("No FX data available. Run data collection to fetch it.")
