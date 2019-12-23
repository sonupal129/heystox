from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract, Candle, SortedStocksList
from datetime import datetime
from django.db.models import Max, Min
from django.core.cache import cache

# Codes Starts Below
def get_cached_liquid_stocks(cached=True, trade_volume=5000000, max_price=300):
    if cached:
        if cache.get(str(datetime.now().date()) + "_today_liquid_stocks"):
            return cache.get(str(datetime.now().date()) + "_today_liquid_stocks")
        else:
            cache.set(str(datetime.now().date()) + "_today_liquid_stocks", get_liquid_stocks(trade_volume=trade_volume, max_price=max_price))
            return get_liquid_stocks(trade_volume=trade_volume, max_price=max_price)
    else:
        return get_liquid_stocks(trade_volume=trade_volume, max_price=max_price)

def select_stocks_for_trading(min_price:int, max_price:int):
      return Symbol.objects.filter(last_day_closing_price__range=(min_price, max_price)).exclude(exchange__name="NSE_INDEX")

def get_liquid_stocks(trade_volume=10000000, min_price=3, max_price=250):
    stocks = select_stocks_for_trading(min_price, max_price)
    return stocks.filter(last_day_vtt__gte=trade_volume)

def get_stocks_for_trading(stocks, date=datetime.now().date(), movement_percent:float=1.2):
    f"""Get stocks whose movement is greater or lower then {movement_percent}"""
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    if nifty_50 == "BUY":
        stocks_for_trade  = [stock for stock in stocks if stock.get_stock_movement(date) and stock.get_stock_movement(date) >= (stock.get_last_day_closing_price() * movement_percent / 100)]
        return stocks_for_trade
    elif nifty_50 == "SELL":
        stocks_for_trade  = [stock for stock in stocks if stock.get_stock_movement(date) and stock.get_stock_movement(date) <= -(stock.get_last_day_closing_price() * movement_percent / 100)]
        return stocks_for_trade
    else:
        return None
    
def add_today_movement_stocks():
    liquid_stocks = get_cached_liquid_stocks()
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    stocks_for_trading = get_stocks_for_trading(stocks=liquid_stocks)
    sorted_stocks_id = []
    if stocks_for_trading:
        for stock in stocks_for_trading:
            try:
                sorted_stock, is_created = SortedStocksList.objects.get_or_create(symbol=stock, entry_type=nifty_50,created_at__date=datetime.now().date())
                sorted_stocks_id.append(sorted_stock.id)
            except:
                continue
        SortedStocksList.objects.filter(created_at__date=datetime.now().date()).exclude(id__in=sorted_stocks_id).delete()





