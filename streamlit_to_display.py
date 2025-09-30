import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

title = "Cross Asset Regime Monitor"
st.set_page_config(title, layout="wide")
st.title(title)

data = pd.read_csv("all_data.csv", index_col=0, delimiter=';')
data = data.ffill().dropna()
returns = data.pct_change()
cum_returns = (1 + returns).cumprod()
cum_returns.index = pd.to_datetime(cum_returns.index) # ensure datetime index
assets = cum_returns.columns
min_date = cum_returns.index[0]
max_date = cum_returns.index[-1]


with st.sidebar:
    selected_assets = st.multiselect("Please select your assets", assets)
    range_start, range_end = st.date_input("Select date range", value= (min_date, max_date))

fig1 = plt.figure(figsize=(10,5))
plt.plot(cum_returns, label = cum_returns.columns)
plt.legend()
plt.title("Cumulative Returns")
plt.xlabel("Date")
plt.ylabel("Cumulative Returns")

st.dataframe(cum_returns)
st.pyplot(fig1)

fig2 = plt.figure(figsize=(10,5))
plt.plot(cum_returns[selected_assets], label = cum_returns[selected_assets].columns)
plt.legend()
plt.title("Cumulative Returns")
plt.xlabel("Date")
plt.ylabel("Selected Assets")

st.pyplot(fig2)