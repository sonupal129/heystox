from market_analysis.models import Symbol
from ta.trend import macd, macd_diff, macd_signal, ema, ema_indicator
from ta.momentum import stoch, stoch_signal
from datetime import datetime
import numpy as np
# Code Start Below Here

def get_macd_data(symbol:object):
    """This function find crossover between macd and macd signal and return signal as buy or sell"""
    df = symbol.get_stock_live_data()
    df["macd"] = macd(df.close_price)
    df["macd_signal"] = macd_signal(df.close_price)
    df["macd_diff"] = macd_diff(df.close_price)
    df["percentage"] = round(df.macd * df.macd_diff /100, 6)
    df["signal"] = np.where(df.macd < df.macd_signal, "SELL", "BUY")
    return df

def get_stochastic_data(symbol:object):
    df = symbol.get_stock_live_data()
    df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
    df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
    df["percentage"] = round(df.stoch * (df.stoch - df.stoch_signal) /100, 6)
    df["signal"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
    return df