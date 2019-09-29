from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract, Candle
import datetime, time

def update_index_data(user, index):
      stock_list = user.get_master_contract(index)
      bulk_symbol = []
      index_obj = MasterContract.objects.get(name=index)
      for stock in stock_list:
            symbol = stock_list.get(stock)
            try:
                  stock = Symbol.objects.get(token=symbol.token, isin=symbol.isin)
                  stock.closing_price = symbol.closing_price
                  stock.save()
            except Symbol.DoesNotExist:
                  bulk_symbol.append(Symbol(exchange=index_obj, token=symbol.token, symbol=symbol.symbol, name=symbol.name,
                        closing_price=symbol.closing_price, tick_size=symbol.tick_size, instrument_type=symbol.instrument_type,
                        isin=symbol.isin))
      Symbol.objects.bulk_create(bulk_symbol)
      return "All Stock Price Updated Sucessfully"

def update_stock_data(user, symbol, interval, start_date, end_date):
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
      start_date = datetime.datetime.strptime(start_date,'%d/%m/%Y').date()
      end_date = datetime.datetime.strptime(end_date,'%d/%m/%Y').date()
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
                  candle = Candle.objects.get(date=datetime.datetime.fromtimestamp(timestamp), symbol=stock)
                  candle.open_price = open_price
                  candle.close_price = close_price
                  candle.high_price = high_price
                  candle.low_price = low_price
                  candle.volume = volume
                  candle.save()
            except Candle.DoesNotExist:
                  bulk_candle_data.append(Candle(open_price=open_price, close_price=close_price, low_price=low_price,
                                                high_price=high_price, volume=volume, date=datetime.datetime.fromtimestamp(timestamp),
                                                symbol=stock, candle_type="M5"))
      Candle.objects.bulk_create(bulk_candle_data)
      return "All Data Updated Sucessfully"



def get_stocks_for_trading(min_price:int, max_price:int):
      return Symbol.objects.filter(closing_price__range=(min_price, max_price))

def is_stock_ohl(symbol, date, candle_type):
    stock_date = datetime.datetime.strptime(date,'%d/%m/%Y').date()
    stock = Symbol.objects.get(symbol=symbol)
    todays_candles = Candle.objects.filter(symbol=stock, candle_type=candle_type, date__date=stock_date)
    first_candle = todays_candles.first()
    first_candle_open_price = first_candle.open_price
    first_candle_low_price = first_candle.low_price
    first_candle_high_price = first_candle.high_price
    current_prices = todays_candles.aggregate(Max("high_price"), Min("low_price"))
    if first_candle_open_price == current_prices.get("high_price__max"):
          return "SELL"
    elif first_candle_open_price == current_prices.get("low_price__min"):
        return "BUY"
    else:
        return False