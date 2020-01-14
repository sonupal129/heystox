from upstox_api.api import *
from market_analysis.models import Symbol, MasterContract, Candle, SortedStocksList
from datetime import datetime
from django.db.models import Max, Min
from django.core.cache import cache
from market_analysis.tasks.tasks import slack_message_sender
# Codes Starts Below
def get_cached_liquid_stocks(cached=True, trade_volume=5000000, max_price=300):
    liquid_stocks_id = get_liquid_stocks(trade_volume=trade_volume, max_price=max_price).values_list("id", flat=True)
    if cached:
        if cache.get(str(datetime.now().date()) + "_today_liquid_stocks"):
            return cache.get(str(datetime.now().date()) + "_today_liquid_stocks")
        else:
            cache.set(str(datetime.now().date()) + "_today_liquid_stocks", liquid_stocks_id)
            return liquid_stocks_id
    else:
        return liquid_stocks_id

def select_stocks_for_trading(min_price:int, max_price:int):
      return Symbol.objects.filter(last_day_closing_price__range=(min_price, max_price)).exclude(exchange__name="NSE_INDEX")

def get_liquid_stocks(trade_volume=10000000, min_price=3, max_price=250):
    stocks = select_stocks_for_trading(min_price, max_price)
    return stocks.filter(last_day_vtt__gte=trade_volume)

def get_stocks_for_trading(stocks, date=datetime.now().date()):
    f"""Get stocks whose movement is greater or lower then"""
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    if nifty_50 == "BUY":
        stocks_for_trade  = [stock for stock in stocks if stock.is_stock_moved_good_for_trading(date=date, movement_percent=1.2)]
        return stocks_for_trade
    elif nifty_50 == "SELL":
        stocks_for_trade  = [stock for stock in stocks if stock.is_stock_moved_good_for_trading(date=date, movement_percent=-1.2)]
        return stocks_for_trade
    else:
        return None
    
def add_today_movement_stocks(movement_percent:float=1.2):
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    stocks_for_trading = get_stocks_for_trading(stocks=liquid_stocks)
    sorted_stocks_name = []
    today_date = datetime.today().date()
    if nifty_50 == "BUY" or nifty_50 == "SELL":
        for stock in stocks_for_trading:
            try:
                obj, is_created = SortedStocksList.objects.get_or_create(symbol=stock, entry_type=nifty_50,created_at__date=today_date)
                sorted_stocks_name.append(obj.symbol.symbol)
            except:
                continue
        slack_message_sender(text=", ".join(sorted_stocks_name) + " Stocks Sorted For Trading in Market Trend")
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=today_date)
    slack_message_sender(channel="#random", text=f"{today_date} date for add_today_movement_stocks function")
    if sorted_stocks:
        deleted_stocks = []
        for stock in sorted_stocks:
            if stock.entry_type == "BUY" or stock.entry_type == "SB" and stock.created_at <= datetime.now() - timedelta(minutes=30):
                if not stock.symbol.is_stock_moved_good_for_trading(date=today_date, movement_percent=1.2):
                    deleted_stocks.append(stock.symbol.symbol)
                    stock.delete()
            elif stock.entry_type == "SELL" or stock.entry_type == "SS" and stock.created_at <= datetime.now() - timedelta(minutes=30):
                if not stock.symbol.is_stock_moved_good_for_trading(date=today_date, movement_percent=-1.2):
                    deleted_stocks.append(stock.symbol.symbol)
                    stock.delete()
        if deleted_stocks:
            slack_message_sender.delay(text=", ".join(deleted_stocks) + " Stocks Deleted from Trending Market")

# Market Sideways Functions
def find_sideways_direction():
    nifty_50 = Symbol.objects.get(symbol="nifty_50")
    nifty_50_movement = nifty_50.get_nifty_movement()
    if nifty_50_movement == "SIDEWAYS":
        nifty_high = nifty_50.get_days_high_low_price(price_type="HIGH")
        nifty_low = nifty_50.get_days_high_low_price(price_type="LOW")
        try:
            nifty_current = nifty_50.get_stock_current_candle().close_price
        except:
            nifty_current = nifty_50.get_day_closing_price()
        nifty_high_variation = nifty_high - nifty_current
        nifty_low_variation = nifty_low - nifty_current
        if nifty_high_variation > 30:
            return nifty_high_variation
        elif nifty_low_variation > -20:
            return nifty_low_variation

def add_stock_on_market_sideways(date=datetime.now().date()):
    nifty_50_point = find_sideways_direction()
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    stocks = get_stocks_for_trading(stocks=liquid_stocks)
    if nifty_50 == "SIDEWAYS" and nifty_50_point:
        if nifty_50_point > 30:
            stocks_for_trade  = [SortedStocksList.objects.get_or_create(symbol=stock, entry_type="SB", created_at__date=date) for stock in stocks if stock.is_stock_moved_good_for_trading(date=date, movement_percent=1.2)]
            slack_message_sender.delay(text=f"List of Sideways Buy Stocks: " +  ", ".join(stock[0].symbol.symbol for stock in stocks_for_trade))
        if nifty_50_point > -20:
            stocks_for_trade  = [SortedStocksList.objects.get_or_create(symbol=stock, entry_type="SS", created_at__date=date) for stock in stocks if stock.is_stock_moved_good_for_trading(date=date, movement_percent=-1.2)]
            slack_message_sender.delay(text=f"List of Sideways Sell Stocks: " + ", ".join(stock[0].symbol.symbol for stock in stocks_for_trade))