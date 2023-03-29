#!/usr/bin/env python3

import requests
import json
import time
import csv
import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
import os

def get_ticker_price():
    price = requests.get('https://www.mercadobitcoin.net/api/BTC/ticker/')
    price = json.loads(price.text)
    return float(price['ticker']['last'])

def get_trades(seconds):
    time_now = int(time.time())
    time_then = time_now - seconds
    trades = requests.get('https://www.mercadobitcoin.net/api/BTC/trades/{0}/{1}'.format(time_then, time_now))
    return trades.json()

def generate_order(order):
    params = order.generate_params()
    tapi_mac = order.generate_mac(params)
    headers = order.generate_headers(tapi_mac)
    order.generate_post(params, headers)

buy_list = []
quantity = 0.0001
walletbrl = 1000
walletbtc = 0
deducted = 0
buyfile = 'buy_list.txt'

if os.path.isfile(buyfile):
    with open(buyfile, 'r') as bfile:
        walletbrl = float(bfile.readline().strip())
        walletbtc = float(bfile.readline().strip())
        deducted = float(bfile.readline().strip())

while True:

    if walletbtc > 0:
        mean_buy = round(deducted / walletbtc, 5)
    else:
        mean_buy = 0
        deducted = 0

    # Example trades data
    trades = get_trades(1000)

    # Extract data from trades
    prices = [trade['price'] for trade in trades]
    timestamps = [trade['date'] for trade in trades]
    current_price = round(get_ticker_price(), 5)

    # Perform linear regression on the prices
    x = np.array(timestamps).reshape(-1, 1)
    y = np.array(prices).reshape(-1, 1)
    reg = LinearRegression().fit(x, y)

    # Initializing regression
    reg_value = round(float(reg.predict(np.array([[timestamps[-1]]]))[0][0]), 5)

    # Fit KMeans model
    kmeans = KMeans(n_clusters=2, n_init='auto')
    kmeans.fit(np.array(prices).reshape(-1, 1))

    # Get cluster centers
    centers = sorted(kmeans.cluster_centers_.ravel())

    # Set lower and upper resistance levels as the midpoint between the cluster centers
    lower_resistance = round(centers[0], 5)
    upper_resistance = round(centers[1], 5)

    # Anticipate conditions
    has_btc = mean_buy != 0
    has_brl = walletbrl > current_price * quantity

    # Calculate cost of transaction
    cost = quantity * current_price

    # Sell if BTC in wallet and ticker greater than previously purchased BTC and upper resistance
    if has_btc and current_price > mean_buy and current_price > upper_resistance:
        trade_type = 'sell'
        walletbrl += cost
        walletbtc -= quantity
        deducted -= cost

    # Buy if money in wallet and ticker less than resistance and regression
    elif has_brl and current_price < lower_resistance and lower_resistance < reg_value:
        trade_type = 'buy'
        walletbrl -= cost
        walletbtc += quantity
        deducted += cost

    # Else hold
    else:
        trade_type = 'hold'

    # Round values
    walletbrl = round(walletbrl, 2)
    walletbtc = round(walletbtc, 4)
    deducted = round(deducted, 2)

    # Create data array for printing
    data = [int(time.time()), trade_type, current_price, lower_resistance, upper_resistance, reg_value, walletbtc, walletbrl, deducted]

    # Save data for next transaction
    with open(buyfile, 'w') as bfile:
        bfile.write(str(walletbrl) + '\n')
        bfile.write(str(walletbtc) + '\n')
        bfile.write(str(deducted))

    # Print data
    print(data)

    # Sleep
    time.sleep(300)
