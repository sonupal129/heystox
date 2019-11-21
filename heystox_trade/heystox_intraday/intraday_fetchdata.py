from market_analysis.models import Symbol, MasterContract, Candle
import time
from datetime import datetime, timedelta
from upstox_api.api import *
import os
from django.core.cache import cache, caches
# Code Starts Below

def update_symbols_data(user, index):
      stock_list = user.get_master_contract(index)
      bulk_symbol = []
      index_obj = MasterContract.objects.get(name=index)
      for stock in stock_list:
            symbol = stock_list.get(stock)
            try:
                  stock = Symbol.objects.get(token=symbol.token, isin=symbol.isin)
                  stock.last_day_closing_price = symbol.closing_price
                  stock.save()
            except Symbol.DoesNotExist:
                  bulk_symbol.append(Symbol(exchange=index_obj, token=symbol.token, symbol=symbol.symbol, name=symbol.name,
                        last_day_closing_price=symbol.closing_price, tick_size=symbol.tick_size, instrument_type=symbol.instrument_type, isin=symbol.isin))
      Symbol.objects.bulk_create(bulk_symbol)
      return "All Stocks Price Updated Sucessfully"

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


def update_all_symbol_candles(user, qs, interval="5 Minute", days=6, end_date=datetime.now()):
      """Takes symbols queryset and upstox user as input and update those symbols candle data"""
      not_updated_stocks = []
      for symbol in qs:
            try:
                  print(get_candles_data(user, symbol, interval, days, end_date))
            except:
                  not_updated_stocks.append(symbol.name)
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

def cache_ticker_data(data:dict):
    redis_cache = caches["redis"]
    try:
        cache_data = redis_cache.get(data.get("symbol"))
        cache_data.append(data)
    except:
        redis_cache.set(str(data.get("symbol")), [data])
    else:
        redis_cache.set(str(data.get("symbol")), cache_data)

def parse_stock_response_data(data:dict):
    """Return only required data by tickerdata model from upstox websocket response"""
    if "instrument" in data:
        del data["instrument"]
    return cache_ticker_data(data)

def get_stock_current_candle(stock_name:str): # Need to refine this function more
    redis_cache = caches["redis"]
    cached_data = redis_cache.get(stock_name)
    first_ticker = cached_data[0]
    current_ticker = cached_data[-1]
    df_ticker = {
        "symbol": first_ticker.get("symbol").lower(),
        "candle_type": "M5",
        "open_price": first_ticker.get("open"),
        "high_price": max(first_ticker.get("high"), current_ticker.get("high")),
        "close_price": current_ticker.get("low"),
        "low_price": min(first_ticker.get("low"), current_ticker.get("low")),
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