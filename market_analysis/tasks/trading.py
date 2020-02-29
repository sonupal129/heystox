from market_analysis.imports import *
from market_analysis.models import Symbol, MasterContract, Candle, SortedStocksList, UserProfile
from .notification_tasks import slack_message_sender
from .intraday_indicator import get_macd_crossover, get_stochastic_crossover
# Codes Starts Below

def get_upstox_user(email):
    try:
        user = UserProfile.objects.get(user__email=email)
    except UserProfile.DoesNotExist:
        return f"user with {email} not found in system"
    profile = None
    try:
        profile = user.get_upstox_user().get_profile()
    except:
        profile = None
    while profile is None:
        try:
            profile = user.get_upstox_user().get_profile()
        except:
            slack_message_sender.delay(text=user.get_authentication_url(), channel="#random")
            sleep(120)
    return user.get_upstox_user()

def select_stocks_for_trading(min_price:int, max_price:int):
      return Symbol.objects.filter(last_day_closing_price__range=(min_price, max_price)).exclude(exchange__name="NSE_INDEX")

def get_liquid_stocks(trade_volume=10000000, min_price=3, max_price=250):
    stocks = select_stocks_for_trading(min_price, max_price)
    return stocks.filter(last_day_vtt__gte=trade_volume)

def get_cached_liquid_stocks(cached=True, trade_volume=5000000, max_price=300):
    cache_id = str(get_local_time().date()) + "_today_liquid_stocks"
    if cached and redis_cache.get(cache_id):
        return redis_cache.get(cache_id)
    liquid_stocks_id = list(get_liquid_stocks(trade_volume=trade_volume, max_price=max_price).values_list("id", flat=True))
    redis_cache.set(cache_id, liquid_stocks_id, 60*30*48)
    return liquid_stocks_id
    

def get_stocks_for_trading():
    f"""Get stocks whose movement is greater or lower then"""
    today_date = get_local_time().date()
    msg = get_stocks_for_trading.__name__ + str(today_date) # DEBUG
    slack_message_sender.delay(text=msg, channel="#test1") # DEBUG
    stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    if nifty_50 == "BUY":
        if redis_cache.get("BUY_stocks_for_trading"):
            return redis_cache.get("BUY_stocks_for_trading")
        stocks_for_trade  = [stock for stock in stocks if stock.is_stock_moved_good_for_trading(movement_percent=1.2)]
        redis_cache.set("BUY_stocks_for_trading", stocks_for_trade, 60*7)
        return stocks_for_trade
    elif nifty_50 == "SELL":
        if redis_cache.get("SELL_stocks_for_trading"):
            return redis_cache.get("SELL_stocks_for_trading")
        stocks_for_trade  = [stock for stock in stocks if stock.is_stock_moved_good_for_trading(movement_percent=-1.2)]
        redis_cache.set("SELL_stocks_for_trading", stocks_for_trade, 60*7)
        return stocks_for_trade
    else:
        return None
    
@celery_app.task(queue="high_priority")
def add_today_movement_stocks(movement_percent:float=1.2):
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    # sorted_stocks_name = []
    today_date = get_local_time().date()
    msg = add_today_movement_stocks.__name__ + str(today_date) # DEBUG
    slack_message_sender.delay(text=msg, channel="#test1") # DEBUG
    movement_on_entry = {
        "BUY" : 1.2,
        "SELL": -1.2,
    }
    if nifty_50 == "BUY" or nifty_50 == "SELL":
        for stock in get_stocks_for_trading():
            try:
                obj, is_created = SortedStocksList.objects.get_or_create(symbol=stock, entry_type=nifty_50,created_at__date=today_date)
                # sorted_stocks_name.append(obj.symbol.symbol)
            except:
                continue
        # slack_message_sender(text=", ".join(sorted_stocks_name) + " Stocks Sorted For Trading in Market Trend")
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=today_date).select_related("symbol").prefetch_related("timestamps")
    if sorted_stocks:
        cached_stocks = []
        deleted_stocks = []
        counter = 0
        for stock in sorted_stocks:
            if stock.created_at <= get_local_time().now() - timedelta(minutes=30) and not stock.symbol.is_stock_moved_good_for_trading(movement_percent=movement_on_entry.get(stock.entry_type)) and not stock.timestamps.all():
                deleted_stocks.append(stock)
                stock.delete()
            else:
                cached_stocks.append(stock)
                # get_stochastic_crossover.apply_async(kwargs={"sorted_stock_id": stock.id}) # Stochastic Crossover Check
                # get_macd_crossover.apply_async(kwargs={"sorted_stock_id": stock.id})# Macd Crossover Check
                counter += 1 #DEBUG
                if counter == 1:#DEBUG
                    slack_message_sender.delay(text=str(stock.symbol.get_stock_live_data()), channel="#celery")#DEBUG
        if deleted_stocks:
            slack_message_sender.delay(text=", ".join(deleted_stocks) + " Stocks Deleted from Trending Market")
        redis_cache.set("todays_sorted_stocks", cached_stocks, 60*30)


# Market Sideways Functions - Need To Work More on below functions
def find_sideways_direction():
    nifty_50 = Symbol.objects.get(symbol="nifty_50")
    nifty_50_movement = nifty_50.get_nifty_movement()
    if nifty_50_movement == "SIDEWAYS":
        nifty_high = nifty_50.get_days_high_low_price(price_type="HIGH")
        nifty_low = nifty_50.get_days_high_low_price(price_type="LOW")
        try:
            nifty_current = nifty_50.get_stock_live_data().iloc[-1].close_price
        except:
            nifty_current = nifty_50.get_day_closing_price()
        nifty_high_variation = nifty_high - nifty_current
        nifty_low_variation = nifty_low - nifty_current
        if nifty_high_variation > 22:
            return nifty_high_variation
        elif nifty_low_variation > -30:
            return nifty_low_variation
 
@celery_app.task(queue="high_priority")
def add_stock_on_market_sideways():
    today_date = get_local_time().date()
    nifty_50_point = find_sideways_direction()
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    if nifty_50 == "SIDEWAYS" and nifty_50_point:
        if nifty_50_point > 22:
            stocks_for_trade  = [SortedStocksList.objects.get_or_create(symbol=stock, entry_type="SELL", created_at__date=today_date) for stock in liquid_stocks if stock.is_stock_moved_good_for_trading(movement_percent=-1.2)]
            slack_message_sender.delay(text=f"List of Sideways Sell Stocks: " +  ", ".join(stock[0].symbol.symbol for stock in stocks_for_trade))
        if nifty_50_point < -30:
            stocks_for_trade  = [SortedStocksList.objects.get_or_create(symbol=stock, entry_type="BUY", created_at__date=today_date) for stock in liquid_stocks if stock.is_stock_moved_good_for_trading(movement_percent=1.2)]
            slack_message_sender.delay(text=f"List of Sideways Buy Stocks: " + ", ".join(stock[0].symbol.symbol for stock in stocks_for_trade))