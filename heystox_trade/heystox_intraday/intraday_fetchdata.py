from market_analysis.models import Symbol, MasterContract, Candle
import time
from datetime import datetime, timedelta
from upstox_api.api import *
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