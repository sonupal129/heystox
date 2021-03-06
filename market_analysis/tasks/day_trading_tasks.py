from .stock_data_import_tasks import (fetch_candles_data)
from .notification_tasks import slack_message_sender
from market_analysis.models import (StrategyTimestamp, SortedStocksList, Symbol, UserProfile, Candle, SortedStockDashboardReport)
from .trading import *
from market_analysis.imports import *
from .strategies.intraday_entry_strategies import *
from .upstox_events_handlers import start_upstox_websocket
# CODE STARTS BELOW

@celery_app.task(queue="low_priority", ignore_result=True)
def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks(cached=False)).values_list("symbol", flat=True)
    message = "Today's Subscribed Stocks:\n" + "| ".join(stock.upper() for stock in liquid_stocks)
    slack_message_sender.delay(text=message)
    return message


@celery_app.task(queue="low_priority", ignore_result=True)
def unsubscribe_today_trading_stocks():
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True)
    message = "Stocks Unsubscribed for Today:\n" + "| ".join(stock.upper() for stock in liquid_stocks)
    slack_message_sender.delay(text=message)
    return message

@celery_app.task(queue="high_priority", ignore_result=True) 
def todays_movement_stocks_add():
    current_time = get_local_time().time()
    start_time = settings.TRADING_START_TIME
    if current_time > start_time:
        add_today_movement_stocks.apply_async()
        return "Function Called"
    return "Function Not Called"


@celery_app.task(queue="high_priority", autoretry_for=(JSONDecodeError,HTTPError), retry_kwargs={'max_retries': 1, 'countdown': 8})
def cache_candles_data(stock_name:str, upstox_user_email="sonupal129@gmail.com", interval:str="1 Minute"):
    try:
        stock = Symbol.objects.get(symbol=stock_name)
    except:
        raise Symbol.DoesNotExist(f"{stock_name} Not Found in Data")
    user = get_upstox_user(email=upstox_user_email)
    user.get_master_contract(stock.exchange.name.upper())
    today_date = get_local_time().date()
    interval_dic = {
        "1 Minute": OHLCInterval.Minute_1,
        "5 Minute": OHLCInterval.Minute_5,
        "10 Minute": OHLCInterval.Minute_10,
        "15 Minute": OHLCInterval.Minute_15,
        }
    stock_data = user.get_ohlc(user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), interval_dic.get(interval), today_date, today_date)
    if stock_data:
        last_candle = stock_data[-1]
        candle = {}
        candle["timestamp"] = last_candle.get("timestamp")
        candle["open"] = float(last_candle.get("open"))
        candle["close"] = float(last_candle.get("close"))
        candle["high"] = float(last_candle.get("high"))
        candle["low"] = float(last_candle.get("low"))
        candle["volume"] = int(last_candle.get("volume"))
        data = redis_cache.get(stock.symbol)
        if data:
            data.append(candle)
            redis_cache.set(stock.symbol, data)
        else:
            data = [candle]
            redis_cache.set(stock.symbol, data)
        return "Data Cached"
    return "Data Not Cached"


@celery_app.task(queue="high_priority")
def create_market_hour_candles(days, fetch_last_candle_number):
    upstox_user = get_upstox_user(email="sonupal129@gmail.com")
    cache_key = str(get_local_time().date()) + "_nifty_daily_gainers_loosers"
    current_time = get_local_time().now()
    nse_imported_stocks_cached_value = redis_cache.get(cache_key)
    symbols = Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True)
    for stock in symbols:
        fetch_candles_data.apply_async(kwargs={"symbol":stock, "days":days, "fetch_last_candle":fetch_last_candle_number}, countdown=27) # By Defautl Fetching 5 Minute Candle
    if nse_imported_stocks_cached_value:
        for stock in nse_imported_stocks_cached_value:
            fetch_candles_data.apply_async(kwargs={"symbol":stock, "days":days}, countdown=29) # By Defautl Fetching 5 Minute Candle, for nify gainers with not limit of fetch last candles
   
    # Now Create Nifty 50 Candle
    fetch_candles_data.apply_async(kwargs={"symbol":"nifty_50", "days":days, "fetch_last_candle":fetch_last_candle_number}, countdown=25)


@celery_app.task(queue="medium_priority")
def delete_last_cached_candles_data():
    for stock in Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True):
        redis_cache.delete(stock)
    redis_cache.delete("nifty_50")
    return "All Cached Candles Deleted Successfully"

@celery_app.task(queue="medium_priority")
def create_stocks_realtime_candle():
    cache_key = str(get_local_time().date()) + "_nifty_daily_gainers_loosers"
    cached_value = redis_cache.get(cache_key)
    symbols = Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True)
    for stock in symbols:
        cache_candles_data.apply_async(kwargs={"stock_name":stock}) #By default one minute is set
    if cached_value:
        for stock in cached_value:
            cache_candles_data.apply_async(kwargs={"stock_name":stock}) #By default one minute is set
    return "All Candles data cached"

@celery_app.task(queue="low_priority")
def create_nifty_50_realtime_candle():
    cache_candles_data.delay(stock_name="nifty_50")
    return f"nifty_50 Data Cached Successfully"


@celery_app.task(queue="high_priority")
def apply_intraday_indicator_on_sorted_stocks():
    movement_on_entry = {
        "BUY" : settings.MARKET_BULLISH_MOVEMENT,
        "SELL": settings.MARKET_BEARISH_MOVEMENT,
    }
    current_time = get_local_time().time()
    start_time = settings.TRADING_START_TIME
    cache_key = str(get_local_time().date()) + "_todays_sorted_stocks"
    cached_value = redis_cache.get(cache_key)
    manual_stocks = list(SortedStocksList.objects.filter(added="ML", created_at__date=get_local_time().date()))
    if manual_stocks:
        cached_value.extend(manual_stocks)
    cached_value = set(cached_value)

    if current_time > start_time:
        if cached_value == None:
            add_today_movement_stocks.apply_async()
            sleep(3)
            cached_value = set(redis_cache.get(cache_key))
        for sorted_stock in cached_value:
            strategies = sorted_stock.symbol.get_strategies(entry_type=sorted_stock.entry_type)
            if strategies.exists():
                for strategy in strategies:
                    data = {"stock_id": sorted_stock.symbol.id}
                    strategy.call_entry_strategy(**data)
        return "Indicator Called"
    return f"Current time {current_time} not > 9:25"

@celery_app.task(queue="medium_priority")
def todays_movement_stocks_add_on_sideways():
    current_time = get_local_time().time()
    start_time = settings.TRADING_START_TIME
    if current_time > start_time:
        add_stock_on_market_sideways.apply_async()
        return "Function Called"
    return "Function Not Called"

@celery_app.task(queue="shower")
def start_websocket(run_in_background=True):
    start_upstox_websocket(run_in_background)
    return "Socket Started"

@celery_app.task(queue="low_priority", ignore_result=True)
def subscribe_stocks_for_realtime_trading(subscribe=True):
    symbols  = Symbol.objects.filter(Q(trade_realtime__contains="BUY") | Q(trade_realtime__contains="SELL")).distinct()
    user = get_upstox_user()
    if symbols.exists() and subscribe:
        data = {symbol.symbol: [symbol.id, symbol] for symbol in symbols}
        cache_key = "_".join([str(get_local_time().date()), "realtime_subscribed_stocks"])
        redis_cache.set(cache_key, data, 9*60*60)

    for symbol in symbols:
        user.get_master_contract(symbol.exchange.name)
        if subscribe:
            try:
                user.subscribe(user.get_instrument_by_symbol(symbol.exchange.name, symbol.symbol), LiveFeedType.Full)
            except:
                pass
        else:
            try:
                user.unsubscribe(user.get_instrument_by_symbol(symbol.exchange.name, symbol.symbol), LiveFeedType.Full)
            except:
                pass