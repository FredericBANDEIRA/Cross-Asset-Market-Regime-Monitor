#Supress warnings from Streamlit
#python streamlit_to_display.py 2>nul
#link https://cross-asset-market-regime-monitor.streamlit.app/

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import plotly.express as px # for interactive plots
from datetime import timedelta
import datetime

title = "Cross Asset Regime Monitor"
st.set_page_config(title, layout="wide")
st.title(title)


data = pd.read_csv("macro.csv", index_col=0)
data = data.ffill().dropna()
returns = data.pct_change()
macro_trends = (1 + returns).cumprod()
macro_trends.index = pd.to_datetime(macro_trends.index) # ensure datetime index
macro = macro_trends.columns
min_date_range = macro_trends.index[0]
max_date_range = macro_trends.index[-1]


data = pd.read_csv("all_data.csv", index_col=0, delimiter=';')
data = data.ffill().dropna()
returns = data.pct_change()
cum_returns = (1 + returns).cumprod()
cum_returns.index = pd.to_datetime(cum_returns.index) # ensure datetime index
assets = cum_returns.columns
min_date_range = cum_returns.index[0]
max_date_range = cum_returns.index[-1]

data = pd.read_csv("vix.csv", index_col=0)
vola = data.ffill().dropna()
vola.index = pd.to_datetime(vola.index) # ensure datetime index
macro = vola.columns
min_date = vola.index[0]
max_date = vola.index[-1]

data = pd.read_csv("sovereign_yields.csv", index_col=0)
yields_us = data.ffill().dropna()
yields_us.index = pd.to_datetime(yields_us.index) # ensure datetime index
macro = yields_us.columns
min_date = yields_us.index[0] + datetime.timedelta(days=365)
max_date = yields_us.index[-1]


with st.sidebar:
    selected_assets = st.multiselect("Please select your assets", assets)
    range_start, range_end = st.date_input("Select date range", value= (min_date_range, max_date_range))
    # fixed_date = st.date_input("Select one date", value= (max_date), min_value=min_date, max_value=max_date)
       
fig0 = px.line(macro_trends[range_start : range_end]).update_layout(
    xaxis_title="Date", 
    yaxis_title="Levels")
st.plotly_chart(fig0)


# st.dataframe(cum_returns)
fig1 = px.line(cum_returns[range_start : range_end]).update_layout(
    xaxis_title="Date", 
    yaxis_title="Price")
st.plotly_chart(fig1)
# st.pyplot(fig1)

# If some assets are selected, plot them
if selected_assets:

    # fig2 = plt.figure(figsize=(10,5))
    # plt.plot(cum_returns[range_start : range_end][selected_assets], label = cum_returns[selected_assets].columns)
    # plt.legend()
    # plt.title("Cumulative Returns")
    # plt.xlabel("Date")
    # plt.ylabel("Selected Assets")

    # st.pyplot(fig2)
    fig2 = px.line(cum_returns[range_start : range_end][selected_assets]).update_layout(
    xaxis_title="Date", 
    yaxis_title="Price")
    st.plotly_chart(fig2)


fig3 = px.line(vola[range_start : range_end]).update_layout(
    xaxis_title="Date", 
    yaxis_title="Level in %")
st.plotly_chart(fig3)

# To create the yield curve
# Define maturity in months for proper spacing
fixed_date = st.slider(
    "Select date:",  # 
    value=max_date.to_pydatetime(),
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime()
)

maturity_months = {
    'DTB4WK': 1/12, 'DGS3MO': 3/12, 'DGS6MO': 6/12,
    'DGS1': 1, 'DGS2': 2, 'DGS3': 3,
    'DGS5': 5, 'DGS7': 7, 'DGS10': 10,
    'DGS20': 20, 'DGS30': 30
}
# Create list of dates
dates_to_get = {
    "Now":pd.Timestamp(fixed_date),
    "90 Days Ago":pd.Timestamp(fixed_date - timedelta(days=90)),
    "180 Days Ago":pd.Timestamp(fixed_date - timedelta(days=180)),
    "365 Days Ago":pd.Timestamp(fixed_date - timedelta(days=365))
}
# Filter only dates that exist in your DataFrame
available_keys = [key for key, date in dates_to_get.items() if date in yields_us.index]
available_dates = [date for date in dates_to_get.values() if date in yields_us.index]

yield_data = pd.DataFrame(yields_us.loc[available_dates])

yields_cols = []
yield_data = yield_data.reset_index()
for i, key in enumerate(available_keys):
    yields_cols.append("Yield " + key)

yield_data = yield_data.T
yield_data.columns =  yields_cols
yield_data = yield_data.reset_index()
yield_data.columns =  ["Maturity"] + yields_cols
yield_data['Maturity'] = yield_data['Maturity'].map(maturity_months)
yield_data = yield_data.iloc[1:] # remove first row which is not needed

# Convert to long format for Plotly
plot_data = yield_data.melt(id_vars=['Maturity'], 
                           var_name='Period', 
                           value_name='Yield')

# Create yield curve plot with multiple lines
fig4 = px.line(
    plot_data,
    x='Maturity',
    y='Yield',
    color='Period',
    title=f"US Treasury Yield Curve Comparison",
    labels={'x': 'Maturity (Years)', 'y': 'Yield (%)'},
    markers=True,
    line_shape='spline'
).update_xaxes(
    tickvals=plot_data['Maturity'].unique(),
    ticktext=['1M', '', '', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y'],
    title="Maturity",
    range=[0, plot_data['Maturity'].max()]  # Start at 0, end at max maturity
).update_traces(
    line=dict(color='blue'),  # Slightly thinner lines
    marker=dict(size=5)    # Smaller markers
)

# Define style mappings
style_map = {
    'Yield Now': {'dash': 'solid', 'width': 4, 'opacity': 1.0},
    'Yield 90 Days Ago': {'dash': 'dash', 'width': 2, 'opacity': 0.8},
    'Yield 180 Days Ago': {'dash': 'dash', 'width': 2, 'opacity': 0.5},
    'Yield 365 Days Ago': {'dash': 'dash', 'width': 2, 'opacity': 0.2}
}

# Apply styles to each trace
for i, period in enumerate(plot_data['Period'].unique()):
    fig4.update_traces(
        selector=dict(name=period),
        line=dict(
            dash=style_map[period]['dash'],
            width=style_map[period]['width']
        ),
        opacity=style_map[period]['opacity']
    )

st.plotly_chart(fig4)


fig5 = px.imshow([[1, 20, 30],
                 [20, 1, 60],
                 [30, 60, 1]])
print(range_start, range_end)
print(type(range_start))
# print(type(cum_returns[pd.to_datetime(range_start)]))
print(cum_returns.index[2])
# print(cum_returns.loc[range_start])
st.plotly_chart(fig5)
print("test")


