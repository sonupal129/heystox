from market_analysis.models import Symbol, MasterContract, Candle
import time
from datetime import datetime, timedelta
from upstox_api.api import *
import os
from django.core.cache import cache, caches
from market_analysis.tasks.tasks import slack_message_sender
import pandas as pd
# Code Starts Below

def get_upstox_user(user_email:str):
    """Returns upstox logged in user object"""
    user = cache.get(user_email + "_upstox_login_user")
    return user

def load_master_contract_data(contract:str=None):
    user = get_upstox_user("sonupal129@gmail.com")
    if contract:
        try:
            user.get_master_contract(contract.upper())
        except:
            raise TypeError ("Obj is not Type of Master Contract")
    else:
        for obj in MasterContract.objects.values():
            user.get_master_contract(obj.get("name"))

def create_symbols_data(user:object, index:str, max_share_price:int=300):
    stock_list = user.get_master_contract(index)
    bulk_symbol = []
    index_obj = MasterContract.objects.get(name=index)
    for stock in stock_list:
        symbol = stock_list.get(stock)
        try:
            stock = Symbol.objects.get(token=symbol.token, isin=symbol.isin)
        except Symbol.DoesNotExist:
            bulk_symbol.append(Symbol(exchange=index_obj, token=symbol.token, symbol=symbol.symbol, name=symbol.name,
                last_day_closing_price=symbol.closing_price, tick_size=symbol.tick_size, instrument_type=symbol.instrument_type, isin=symbol.isin))
    Symbol.objects.bulk_create(bulk_symbol)
    return "All Stocks Data Updated Sucessfully"

def get_candles_data(user, symbol:str, interval="5 Minute", days=6, end_date=datetime.now().date()):
    interval_dic = {
        "5 Minute": OHLCInterval.Minute_5,
        "10 Minute": OHLCInterval.Minute_10,
        "15 Minute": OHLCInterval.Minute_15,
    }
    candle_dic = {
        "5 Minute": "M5",
        "10 Minute": "M10",
        "15 Minute": "M15",
    }
    candle_interval = interval_dic.get(interval, "5 Minute")
    start_date = end_date - timedelta(days)
    try:
        stock = Symbol.objects.get(symbol=symbol)
    except Symbol.DoesNotExist:
        return "No Stock Found Please Try with Another"
    stock_data = user.get_ohlc(user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), candle_interval, start_date, end_date)
    bulk_candle_data = []
    for data in stock_data:
        timestamp = int(data.get("timestamp")[:10])
        open_price = float(data.get("open"))
        close_price = float(data.get("close"))
        high_price = float(data.get("high"))
        low_price = float(data.get("low"))
        volume = int(data.get("volume"))
        try:
            candle = Candle.objects.get(date=datetime.fromtimestamp(timestamp), symbol=stock)
            # candle.open_price = open_price
            # candle.close_price = close_price
            # candle.high_price = high_price
            # candle.low_price = low_price
            # candle.volume = volume
            # candle.save()
        except Candle.DoesNotExist:
            bulk_candle_data.append(Candle(open_price=open_price, close_price=close_price, low_price=low_price,
                                        high_price=high_price, volume=volume, date=datetime.fromtimestamp(timestamp),
                                        symbol=stock, candle_type="M5"))
    Candle.objects.bulk_create(bulk_candle_data)
    return "{0} Candles Data Imported Sucessfully".format(symbol)


def update_all_symbol_candles(user, qs, interval="5 Minute", days=6, end_date=datetime.now().date()):
    """Takes symbols queryset and upstox user as input and update those symbols candle data"""
    not_updated_stocks = []
    updated_stocks = []
    for symbol in qs:
            try:
                print(get_candles_data(user, symbol, interval, days, end_date))
                updated_stocks.append(symbol.name)
            except:
                not_updated_stocks.append(symbol.name)
    if not_updated_stocks:
        message = " | ".join(not_updated_stocks)
        slack_message_sender.delay(text=f"Stocks Data Not Updated For: {message}")
    if updated_stocks:
        message = " | ".join(updated_stocks)
        slack_message_sender.delay(text=f"Stocks Data Updated For: {message}")
    return "All Stocks Data has been imported except these {0} ".format(not_updated_stocks)

# def add_tickerdata_to_csv(data):
#     dirpath = os.path.join(os.path.dirname(os.getcwd()),'ticketdata_csv')
#     df = pd.DataFrame(data)
#     filepath = os.path.join(dirpath, "tickerdata.csv")
#     if not os.path.exists(dirpath):
#         os.mkdir(dirpath)
#         df.to_csv(filepath)
#     else:
#         df.to_csv(filepath, mode="a", header=False)

# def cache_ticker_data(data:dict):
#     redis_cache = caches["redis"]
#     try:
#         cache_data = redis_cache.get(data.get("symbol"))
#         cache_data.append(data)
#     except:
#         redis_cache.set(str(data.get("symbol")), [data])
#     else:
#         redis_cache.set(str(data.get("symbol")), cache_data)

# def parse_stock_response_data(data:dict):
#     """Return only required data by tickerdata model from upstox websocket response"""
#     if "instrument" in data:
#         del data["instrument"]
#     return cache_ticker_data(data)

def cache_candles_data(user:object, stock:object, interval:str="1 Minute", start_day:int=0, end_date=datetime.now().date()): #Need to work more on this function bc correct candle nahi aa rhi hai 
    interval_dic = {
        "1 Minute": OHLCInterval.Minute_1,
        "5 Minute": OHLCInterval.Minute_5,
        "10 Minute": OHLCInterval.Minute_10,
        "15 Minute": OHLCInterval.Minute_15,
        }
    redis_cache = caches["redis"]
    start_date = end_date - timedelta(start_day)
    stock_data = user.get_ohlc(user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), interval_dic.get(interval), start_date, end_date)
    *rest_candles, second_last_candle, last_candle = stock_data
    data = [second_last_candle, last_candle]
    redis_cache.set(stock.symbol, data)

def get_stock_current_candle(stock_name:str): # Need to refine this function more
    redis_cache = caches["redis"]
    cached_data = redis_cache.get(stock_name)
    first_ticker, current_ticker = cached_data
    df_ticker = {
        "candle_type": "M5",
        "open_price": first_ticker.get("open"),
        "high_price": max(data.get("high") for data in cached_data),
        "close_price": current_ticker.get("close"),
        "low_price": min(data.get("low") for data in cached_data),
        "volume": current_ticker.get("vtt"),
        "atp": current_ticker.get("atp"),
        "total_buy_quantity": current_ticker.get("total_buy_quantity"),
        "total_sell_quantity": current_ticker.get("total_sell_quantity"),
        "lower_circuit": current_ticker.get("lower_circuit"),
        "upper_circuit": current_ticker.get("upper_circuit"),
        "bids": {},
        "asks": {},
        "date": datetime.fromtimestamp(int(current_ticker.get("timestamp")[:10]))
    }
    return df_ticker

def get_stock_live_data(stock_name:str):
    symbol = Symbol.objects.get(symbol=stock_name)
    stock_data = symbol.get_stock_data()
    current_candle_data = get_stock_current_candle(stock_name)
    df1 = pd.DataFrame(list(stock_data.values("candle_type", "open_price", "high_price", "low_price", "close_price", "volume", "total_buy_quantity", "total_sell_quantity", "date")))
    df2 = pd.DataFrame(current_candle_data, index=[0])
    df = pd.concat([df1, df2], ignore_index=True)
    return df