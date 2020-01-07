from market_analysis.models import Symbol, MasterContract, Candle, UserProfile
import time
from datetime import datetime, timedelta
from upstox_api.api import *
import os
from django.core.cache import cache, caches
from market_analysis.tasks.tasks import slack_message_sender
import pandas as pd
from django.core.exceptions import ObjectDoesNotExist
# Code Starts Below

def get_upstox_user(email):
    profile = None
    try:
        user = UserProfile.objects.get(user__email=email)
    except UserProfile.DoesNotExist:
        return f"user with {email} not found in system"
    try:
        profile = user.get_upstox_user().get_profile().get("email")
    except:
        profile = None
    if user:
        while profile != email:
            try:
                profile = user.get_upstox_user().get_profile().get("email")
            except:
                slack_message_sender.delay(text=user.get_authentication_url())
                time.sleep(58)
        return user.get_upstox_user()
    
def load_master_contract_data(contract:str=None):
    user = get_upstox_user(email="sonupal129@gmail.com")
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
            candle.open_price = open_price
            candle.close_price = close_price
            candle.high_price = high_price
            candle.low_price = low_price
            candle.volume = volume
            candle.save()
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
        # message = " | ".join(updated_stocks)
        # slack_message_sender.delay(text=f"Stocks Data Updated For: {message}")
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
    if start_day == 0: 
        start_date = end_date
    else:
        start_date = end_date - timedelta(start_day)
    stock_data = user.get_ohlc(user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), interval_dic.get(interval), start_date, end_date)
    if stock_data:
        last_candle = stock_data[-1]
        candle["timestamp"] = last_candle.get("timestamp")
        candle["open"] = float(last_candle.get("open"))
        candle["close"] = float(last_candle.get("close"))
        candle["high"] = float(last_candle.get("high"))
        candle["low"] = float(last_candle.get("low"))
        candle["volume"] = int(last_candle.get("volume"))
        data = redis_cache.get(stock.symbol)
        if data:
            data.append(candle)
            redis_cache.set(stock.symbol, data)
        else:
            data = [last_candle]
            redis_cache.set(stock.symbol, data)