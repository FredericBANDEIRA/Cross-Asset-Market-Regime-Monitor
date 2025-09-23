# Dashboard with equity (SPY), forex (USD), commodities (Gold ($GC=F), crude oil ($WTI or $USD), wheat (ZW=F)), bonds (Inflation-linked bonds (^TNX))
# Data about growth, inflation, volatility, and yield.
# Data goes back as far as possible, with widget slider to choose timeframe.

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
#import streamlit as st

def data_download(ticker, filename):
    data = yf.download(ticker, period="20y", interval="1d",)["Close"]
    data.to_csv(filename)
    return data

ticker_filename = {
    "SPY" : "spy.csv",
    "DX-Y.NYB" : "usd.csv",
    "GC=F" : "gold.csv",
    "WTI" : "oil.csv",
    "ZW=F" : "wheat.csv",
    "^TNX" : "bond.csv"
}

# for ticker, filename in ticker_filename.items():
#     data_download(ticker, filename)


# Sanity Checks
# Check for missing values
def check_na(data):
    null_sum = data.isna().sum()
    null_percentage = null_sum/len(data)
    print(f"Ratio of missing values: {null_percentage}")

def deal_with_na(data):
    return data.ffill().bfill()

def scale_data(data):
    data["base100"] = (data['SPY'].pct_change() + 1).cumprod()*100
    data.loc[data.index[0], "base100"] = 100


def get_data(ticker, filename):
    data = yf.download(ticker, period="20y", interval="1d",)["Close"]
    check_na(data)
    deal_with_na(data)
    scale_data(data)
    data.to_csv(filename)
    data["base100"].plot(label = ticker.upper())
    plt.ylabel("SPY Closing Price")
    plt.title("SPY CLosing Price Over Time")
    

get_data("SPY", "spy.csv")
plt.legend()
plt.show()
"""
for next time:
- then make a bigger function which call all previous functions
- create a function that plot data
- we'll use streamlit
"""