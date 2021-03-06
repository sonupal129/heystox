from market_analysis.imports import *
from market_analysis.models import Symbol, MasterContract, Candle, SortedStocksList, UserProfile, MarketHoliday
from .notification_tasks import slack_message_sender

from .users_tasks import login_upstox_user
# Codes Starts Below

def get_upstox_user(email="sonupal129@gmail.com"):
    cache_key = "_".join([str(get_local_time().date()), email, "local_upstox_user"])
    profile = cache.get(cache_key)
    if profile is None:
        user = UserProfile.objects.get(user__email=email)
        upstox_user_profile = user.get_upstox_user()
        cache.set(cache_key, user.get_upstox_user(), 30*20)
        return upstox_user_profile
    return profile

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
    
@celery_app.task(queue="high_priority", ignore_result=True)
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
                SortedStocksList.objects.get_or_create(symbol=stock, entry_type=nifty_50, created_at__date=today_date)
            except:
                continue
        # slack_message_sender(text=", ".join(sorted_stocks_name) + " Stocks Sorted For Trading in Market Trend")
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=today_date, added="AT").select_related("symbol").prefetch_related("timestamps")
    nifty_imported_stocks_cache_key = str(get_local_time().date()) + "_nifty_daily_gainers_loosers"
    nifty_imported_stocks_cached_value = redis_cache.get(nifty_imported_stocks_cache_key)
    if nifty_imported_stocks_cached_value == None:
        imported_stocks = SortedStocksList.objects.filter(created_at__date=today_date, added="AT").exclude(symbol_id__in=get_cached_liquid_stocks()).values_list("symbol__symbol", flat=True)
        redis_cache.set(nifty_imported_stocks_cache_key, imported_stocks, 60*30)
    cached_value = redis_cache.get(cache_key)
    if sorted_stocks:
        deleted_stocks = []
        for stock in sorted_stocks:
            try:
                not_good_movement = stock.created_at <= get_local_time().now() - timedelta(minutes=30) and not stock.symbol.is_stock_moved_good_for_trading(movement_percent=movement_on_entry.get(stock.entry_type)) and not stock.timestamps.all()
            except:
                continue
            if not_good_movement:
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


# Market Sideways Functions - Need To Work More on below functions
def find_sideways_direction():
    nifty_50 = Symbol.objects.get(symbol="nifty_50")
    nifty_50_movement = nifty_50.get_nifty_movement()
    if nifty_50_movement == "SIDEWAYS":
        nifty_high = nifty_50.get_stock_high_low_price(price_type="HIGH")
        nifty_low = nifty_50.get_stock_high_low_price(price_type="LOW", side="lowest")
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
 
@celery_app.task(queue="high_priority", ignore_result=True)
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


@celery_app.task(queue="low_priority", ignore_result=True)
def add_manual_sorted_stocks():
    """Function add stocks automatically as manual stocks which get stocks get seleted by manually
    and stocks dosen't affect by movement strategy directly applied on these stocks"""
    symbols  = Symbol.objects.filter(Q(trade_manually__contains="BUY") | Q(trade_manually__contains="SELL"))
    nifty_50_movement = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    today_date = get_local_time().date()
    current_time = get_local_time().time()
    if current_time > settings.TRADING_START_TIME:
        for symbol in symbols:
            for entry_type in symbol.trade_manually:
                if entry_type == nifty_50_movement:
                    SortedStocksList.objects.update_or_create(symbol=symbol, entry_type=entry_type, created_at__date=today_date, defaults={"added" : "ML" })
                elif nifty_50_movement == "SIDEWAYS":
                    try:
                        stock = SortedStocksList.objects.get(symbol=symbol, entry_type=entry_type, created_at__date=today_date, added="ML")
                        if not stock.timestamps.all():
                            stock.delete()
                    except:
                        pass
        return True
    return False

@celery_app.task(queue="low_priority", ignore_result=True)
def update_remove_manually_traded_stocks(stock_add:bool=True):
    if stock_add:
        Symbol.objects.filter(id__in=get_cached_liquid_stocks(cached=False)).update(trade_manually=["BUY","SELL"])
    else:
        Symbol.objects.all().update(trade_manually=None)
    return True