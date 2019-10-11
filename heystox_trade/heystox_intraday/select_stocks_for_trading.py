from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract, Candle
import datetime, time
from django.db.models import Max, Min


# Codes Starts Below

def get_stocks_for_trading(min_price:int, max_price:int):
      return Symbol.objects.filter(last_day_closing_price__range=(min_price, max_price))

def get_liquid_stocks(trade_volume=10000000):
    stocks = get_stocks_for_trading(3, 250)
    return stocks.filter(last_day_vtt__gte=total_trade_volume)


#  Now Make Function for Feed Data



