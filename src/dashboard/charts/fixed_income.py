import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta
from dashboard.config import PLOTLY_TEMPLATE, US_MATURITY_MAP, RECESSIONS


def render(*, yields_us, ecb_aaa, ecb_all, indicators, start_dt, end_dt):
    """Render the Fixed Income tab contents."""
    st.subheader("Sovereign Yield Curves")

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
