from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract, Candle
import datetime, time
from django.db.models import Max, Min


# Codes Starts Below

def get_stocks_for_trading(min_price:int, max_price:int):
      return Symbol.objects.filter(last_day_closing_price__range=(min_price, max_price))

def get_liquid_stocks(trade_volume=10000000):
    stocks = get_stocks_for_trading(3, 250)
    return stocks.filter(last_day_vtt__gte=trade_volume)

def get_nifty_movement(data=datetime.now()):
    "Function Returns Nifty 50 Movement Only"
    nifty_50 = Symbol.objects.get(symbol="nifty_50")
    current_price = Candle.objects.filter(symbol=self, date__date=date.date()).last().close_price
    diff = current_price - self.last_day_closing_price
    if diff >= 32:
        return "BUY"
    elif diff <= -32:
        return "SELL"
    else:
        return "SIDEWAYS" 

#  Now Make Function for Feed Data



