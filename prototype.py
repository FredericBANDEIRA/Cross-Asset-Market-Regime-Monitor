# Dashboard with equity (SPY), forex (USD), commodities (Gold ($GC=F), crude oil ($WTI or $USD), wheat (ZW=F)), bonds (Inflation-linked bonds (^TNX))
# Data about growth, inflation, volatility, and yield.
# Data goes back as far as possible, with widget slider to choose timeframe.

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
#import streamlit as st

def data_download(ticker, filename):
    data = yf.download(ticker, period="max", interval="1d",)["Close"]
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

sanitized_ticker = {ticker: filename.replace('.csv', '') for ticker, filename in ticker_filename.items()}

data_dic={}

for ticker, filename in ticker_filename.items():
    data_dic[ticker] = data_download(ticker, filename)

# Sanity Checks
# Check for missing values
def check_na(data):
    null_sum = data.isna().sum()
    null_percentage = null_sum/len(data)
    print(f"Ratio of missing values: {null_percentage}")

def deal_with_na(data):
    return data.ffill().bfill()

def fill_missing_values(df):
    '''
    Fill missing values using FFILL method
    '''
    df = df.ffill().dropna()
    return df

def scale_data(data):
    data["base100"] = (data['SPY'].pct_change() + 1).cumprod()*100
    data.loc[data.index[0], "base100"] = 100

def plot_df(ticker):
    data = pd.read_csv(ticker_filename[ticker])

    data['Date'] = pd.to_datetime(data['Date'])

    plt.figure()
    plt.title(sanitized_ticker[ticker])
    plt.plot(data["Date"], data[ticker])
    plt.savefig(sanitized_ticker[ticker])

def get_data(ticker, filename):
    data = yf.download(ticker, period="20y", interval="1d",)["Close"]
    check_na(data)
    deal_with_na(data)
    scale_data(data)
    data.to_csv(filename)
    data["base100"].plot(label = ticker.upper())
    plt.ylabel("SPY Closing Price")
    plt.title("SPY CLosing Price Over Time")
    

for ticker in ticker_filename.keys():
    print(f"Checking {ticker}")
    data = pd.read_csv(ticker_filename[ticker], index_col=0, parse_dates=True)
    check_na(data)
    print("")
    data = fill_missing_values(data)
    plot_df(ticker)


# get_data("SPY", "spy.csv")
# plt.legend()
# plt.show()
"""
for next time:
- then make a bigger function which call all previous functions
- create a function that plot data
- we'll use streamlit
"""