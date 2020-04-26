from market_analysis.imports import *
from market_analysis.models import Symbol, MasterContract, Candle, SortedStocksList, UserProfile, MarketHoliday
from .notification_tasks import slack_message_sender

from .users_tasks import login_upstox_user
# Codes Starts Below

def get_upstox_user(email="sonupal129@gmail.com"):
    user = UserProfile.objects.get(user__email=email)
    cache_key = str(get_local_time().date()) +  "_local_upstox_user"
    profile = cache.get(cache_key)
    login_attempt_counter = cache.get("login_attempt_counter")
    if profile is None:
        try:
            upstox_user_profile = user.get_upstox_user().get_profile()
            cache.set(cache_key, user.get_upstox_user(), 30*10)
        except:
            if login_attempt_counter is None:
                cache.set("login_attempt_counter", 1)
            else:
                cache.set("login_attempt_counter", login_attempt_counter + 1)
            login_upstox_user.delay(email)
            sleep(2)
            if login_attempt_counter == 60:
                cache.delete("login_attempt_counter")
                slack_message_sender.delay(text=user.get_authentication_url(), channel="#random")
    return cache.get(cache_key)

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
    stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    if nifty_50 == "BUY":
        if redis_cache.get("BUY_stocks_for_trading"):
            return redis_cache.get("BUY_stocks_for_trading")
        stocks_for_trade  = [stock for stock in stocks if stock.is_stock_moved_good_for_trading(movement_percent=settings.MARKET_BULLISH_MOVEMENT)]
        redis_cache.set("BUY_stocks_for_trading", stocks_for_trade, 60*7)
        return stocks_for_trade
    elif nifty_50 == "SELL":
        if redis_cache.get("SELL_stocks_for_trading"):
            return redis_cache.get("SELL_stocks_for_trading")
        stocks_for_trade  = [stock for stock in stocks if stock.is_stock_moved_good_for_trading(movement_percent=settings.MARKET_BEARISH_MOVEMENT)]
        redis_cache.set("SELL_stocks_for_trading", stocks_for_trade, 60*7)
        return stocks_for_trade
    else:
        return None
    
@celery_app.task(queue="high_priority")
def add_today_movement_stocks(movement_percent:float=settings.MARKET_BULLISH_MOVEMENT):
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    today_date = get_local_time().date()
    cache_key = str(today_date) + "_todays_sorted_stocks"
    movement_on_entry = {
        "BUY" : settings.MARKET_BULLISH_MOVEMENT,
        "SELL": settings.MARKET_BEARISH_MOVEMENT,
    }
    if nifty_50 == "BUY" or nifty_50 == "SELL":
        for stock in get_stocks_for_trading():
            try:
                obj, is_created = SortedStocksList.objects.get_or_create(symbol=stock, entry_type=nifty_50, created_at__date=today_date)
                # sorted_stocks_name.append(obj.symbol.symbol)
            except:
                continue
        # slack_message_sender(text=", ".join(sorted_stocks_name) + " Stocks Sorted For Trading in Market Trend")
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=today_date).select_related("symbol").prefetch_related("timestamps")
    nifty_imported_stocks_cache_key = str(get_local_time().date()) + "_nifty_daily_gainers_loosers"
    nifty_imported_stocks_cached_value = redis_cache.get(nifty_imported_stocks_cache_key)
    if nifty_imported_stocks_cached_value == None:
        imported_stocks = SortedStocksList.objects.filter(created_at__date=today_date).exclude(symbol_id__in=get_cached_liquid_stocks()).values_list("symbol__symbol", flat=True)
        redis_cache.set(nifty_imported_stocks_cache_key, imported_stocks, 60*30)
    cached_value = redis_cache.get(cache_key)
    if sorted_stocks:
        deleted_stocks = []
        counter = 0
        for stock in sorted_stocks:
            if stock.created_at <= get_local_time().now() - timedelta(minutes=30) and not stock.symbol.is_stock_moved_good_for_trading(movement_percent=movement_on_entry.get(stock.entry_type)) and not stock.timestamps.all():
                deleted_stocks.append(stock.symbol.symbol)
                if cached_value and stock in cached_value:
                    cached_value = cached_value.remove(stock)
                    redis_cache.set(cache_key, cached_value)
                stock.delete()
            else:
                if cached_value == None:
                    cached_value = [stock]
                    redis_cache.set(cache_key, cached_value, 60*30)
                elif stock not in cached_value:
                    cached_value.append(stock)
                    redis_cache.set(cache_key, cached_value, 60*30)
        if deleted_stocks:
            slack_message_sender.delay(text=", ".join(deleted_stocks) + " Stocks Deleted from Trending Market")


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
            stocks_for_trade  = [SortedStocksList.objects.get_or_create(symbol=stock, entry_type="SELL", created_at__date=today_date) for stock in liquid_stocks if stock.is_stock_moved_good_for_trading(movement_percent=settings.MARKET_BEARISH_MOVEMENT)]
            slack_message_sender.delay(text=f"List of Sideways Sell Stocks: " +  ", ".join(stock[0].symbol.symbol for stock in stocks_for_trade))
        if nifty_50_point < -30:
            stocks_for_trade  = [SortedStocksList.objects.get_or_create(symbol=stock, entry_type="BUY", created_at__date=today_date) for stock in liquid_stocks if stock.is_stock_moved_good_for_trading(movement_percent=settings.MARKET_BULLISH_MOVEMENT)]
            slack_message_sender.delay(text=f"List of Sideways Buy Stocks: " + ", ".join(stock[0].symbol.symbol for stock in stocks_for_trade))