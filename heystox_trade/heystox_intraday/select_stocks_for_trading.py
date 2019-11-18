from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract, Candle, SortedStocksList
from datetime import datetime
from django.db.models import Max, Min


# Codes Starts Below
def get_cached_liquid_stocks():
    try:
        return cache.get(str(datetime.now().date()) + "_today_liquid_stocks")
    except:
        return None

def select_stocks_for_trading(min_price:int, max_price:int):
      return Symbol.objects.filter(last_day_closing_price__range=(min_price, max_price))

def get_liquid_stocks(trade_volume=10000000):
    stocks = select_stocks_for_trading(3, 250)
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

def get_stocks_for_trading(stocks, date=datetime.now(), movement_percent:int=1.2):
    f"""Get stocks whose movement is greater or lower then {movement_percent}"""
    nifty_50 = get_nifty_movement(date=date)
    if nifty_50 == "BUY":
        stocks_for_trade  = [stock for stock in stocks if stock.get_stock_movement(date) >= movement_percent ]
    elif nifty_50 == "SELL":
        stocks_for_trade  = [stock for stock in stocks if stock.get_stock_movement(date) <= -movement_percent ]
    return stocks_for_trade
    
def add_today_movement_stocks():
    liquid_stocks = get_cached_liquid_stocks()
    nifty_50 = get_nifty_movement(date=datetime.now())
    stocks_for_trading = get_stocks_for_trading(qs=liquid_stocks)
    for stock in stocks_for_trading:
        if nifty_50 == "BUY":
            SortedStocksList.objects.get_or_create(symbol=stock.symbol, stock_type="B")
        elif nifty_50 == "SELL":
            SortedStocksList.objects.get_or_create(symbol=stock.symbol, stock_type="S")





