import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dashboard.config import PLOTLY_TEMPLATE, GROWTH_HIGH, GROWTH_LOW, INFLATION_HIGH, INFLATION_LOW


def render(*, macro_trends, vola, indicators, yields_us, macro_yoy, start_dt, end_dt):
    """Render the Macro & Rates tab contents."""
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
