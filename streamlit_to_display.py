#Supress warnings from Streamlit
#python streamlit_to_display.py 2>nul


import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import plotly.express as px # for interactive plots
from datetime import timedelta

title = "Cross Asset Regime Monitor"
st.set_page_config(title, layout="wide")
st.title(title)


data = pd.read_csv("macro.csv", index_col=0)
data = data.ffill().dropna()
returns = data.pct_change()
macro_trends = (1 + returns).cumprod()
macro_trends.index = pd.to_datetime(macro_trends.index) # ensure datetime index
macro = macro_trends.columns
min_date = macro_trends.index[0]
max_date = macro_trends.index[-1]


data = pd.read_csv("all_data.csv", index_col=0, delimiter=';')
data = data.ffill().dropna()
returns = data.pct_change()
cum_returns = (1 + returns).cumprod()
cum_returns.index = pd.to_datetime(cum_returns.index) # ensure datetime index
assets = cum_returns.columns
min_date = cum_returns.index[0]
max_date = cum_returns.index[-1]

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
min_date = yields_us.index[0]
max_date = yields_us.index[-1]


with st.sidebar:
    selected_assets = st.multiselect("Please select your assets", assets)
    range_start, range_end = st.date_input("Select date range", value= (min_date, max_date))
    fixed_date = st.date_input("Select date range", value= (max_date))
    
fig0 = px.line(macro_trends[range_start : range_end]).update_layout(
    xaxis_title="Date", 
    yaxis_title="Levels")
st.plotly_chart(fig0)

# fig0 = plt.figure(figsize=(10,5))
# plt.plot(macro_trends[range_start : range_end], label = macro_trends.columns)
# plt.legend()
# plt.title("Macro Trends")
# plt.xlabel("Date")
# plt.ylabel("Levels")

# st.pyplot(fig0)

# fig1 = plt.figure(figsize=(10,5))
# plt.plot(cum_returns[range_start : range_end], label = cum_returns.columns)
# plt.legend()
# plt.title("Cumulative Returns")
# plt.xlabel("Date")
# plt.ylabel("Cumulative Returns")

st.dataframe(cum_returns)
fig1 = px.line(cum_returns[range_start : range_end]).update_layout(
    xaxis_title="Date", 
    yaxis_title="Price")
st.plotly_chart(fig1)
print(cum_returns.head())
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
maturity_months = {
    'DGS1MO': 1/12, 'DGS3MO': 3/12, 'DGS6MO': 6/12,
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

print(yield_data)
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
print(yield_data)

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
    tickvals=yield_data['Maturity'],
    ticktext=['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y'],
    title="Maturity"
)

fig4.update_layout(
    legend_title_text="Time Period"
)

st.plotly_chart(fig4)