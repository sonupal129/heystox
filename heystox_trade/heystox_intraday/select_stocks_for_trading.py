from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract, Candle
import datetime, time
from django.db.models import Max, Min


# Codes Starts Below

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

def is_stock_pdhl(symbol, date, candle_type):
    today = datetime.strptime(date,'%d/%m/%Y').date()
    yesterday = datetime.strptime(date,'%d/%m/%Y').date() - timedelta(1)
    stock = Symbol.objects.get(symbol=symbol)
    candles = Candle.objects.filter(symbol=stock, candle_type=candle_type, date__range=[yesterday, today + timedelta(1)])
    last_day_closing_price = candles.filter(date__date=yesterday).last().close_price
    last_day_opening_price = candles.filter(date__date=yesterday).first().open_price
    today_opening_price = candles.filter(date__date=today).first().open_price
    if last_day_opening_price > last_day_closing_price > today_opening_price:
        return "SELL"
    elif last_day_opening_price < last_day_closing_price < today_opening_price:
        return "BUY"
    else:
        return False