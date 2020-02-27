from .stock_data_import_tasks import (fetch_candles_data)
from .notification_tasks import slack_message_sender
from market_analysis.models import (StrategyTimestamp, SortedStocksList, Symbol, UserProfile, Candle, Indicator, SortedStockDashboardReport)
from .trading import *
from market_analysis.imports import *


# CODE STARTS BELOW

@celery_app.task(queue="low_priority")
def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks(cached=False)).values_list("symbol", flat=True)
    message = "Today's Subscribed Stocks:\n" + "| ".join(stock.upper() for stock in liquid_stocks)
    slack_message_sender.delay(text=message)
    # upstox_user = get_upstox_user("sonupal129@gmail.com")
    # upstox_user.set_on_quote_update(parse_stock_response_data)
    # upstox_user.get_master_contract("NSE_EQ")
    # for stock in liquid_stocks:
    #     upstox_user.subscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    # upstox_user.get_master_contract("NSE_INDEX")
    # upstox_user.subscribe(upstox_user.get_instrument_by_symbol("NSE_INDEX", "nifty_50"), LiveFeedType.Full)
    # upstox_user.start_websocket(True)
    return message


@celery_app.task(queue="low_priority")
def unsubscribe_today_trading_stocks():
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True)
    message = "Stocks Unsubscribed for Today:\n" + "| ".join(stock.upper() for stock in liquid_stocks)
    slack_message_sender.delay(text=message)
    # upstox_user = get_upstox_user("sonupal129@gmail.com")
    # upstox_user.get_master_contract("NSE_EQ")
    # for stock in liquid_stocks:
    #     upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    # upstox_user.get_master_contract("NSE_INDEX")
    # upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol("NSE_INDEX", "nifty_50"), LiveFeedType.Full)
    return message

@celery_app.task(queue="high_priority") #Check more for minute how to start-stop after specific time
def todays_movement_stocks_add():
    current_time = get_local_time.time()
    start_time = time(9,20)
    if current_time > start_time:
        add_today_movement_stocks.apply_async()
        return "Function Called"
    return "Function Not Called"

@celery_app.task(queue="low_priority") 
def find_ohl_stocks():
    current_time = get_local_time.time()
    start_time = time(9,25)
    if current_time > start_time:
        sorted_stocks = redis_cache.get("todays_sorted_stocks")
        if sorted_stocks:
            todays_timestamps = StrategyTimestamp.objects.select_related("stock", "indicator").filter(indicator__name="OHL", timestamp__date=get_local_time.date())
            for stock in sorted_stocks:
                timestamps = todays_timestamps.filter(stock=stock)
                ohl_condition = stock.symbol.is_stock_ohl()
                if ohl_condition:
                    if stock.entry_type == ohl_condition and not timestamps.exists():
                        ohl_indicator = Indicator.objects.get(name="OHL")
                        StrategyTimestamp.objects.create(indicator=ohl_indicator, stock=stock, timestamp=get_local_time.now())
                    elif stock.entry_type != ohl_condition:
                        timestamps.delete()
                    elif timestamps.count() > 1:
                        timestamps.exclude(id=timestamps.first().id).delete()
            return "OHL Updated"
        return "No Sorted Stocks Cached"
    return f"Time {current_time} not > 9:25"

@celery_app.task(queue="low_priority") # Will Work on These Functions Later
def is_stock_pdhl(obj_id):
    stock = SortedStocksList.objects.get(id=obj_id)
    if stock.symbol.is_stock_pdhl() == stock.entry_type:
        pdhl_indicator = Indicator.objects.get(name="PDHL")
        pdhl, is_created = StrategyTimestamp.objects.get_or_create(indicator=pdhl_indicator, stock=stock)
        pdhl.timestamp = get_local_time.now()
        pdhl.save()
        return "Stamp Created"


@celery_app.task(queue="low_priority") # Will Work on These Functions Later
def take_entry_for_long_short(obj_id):
    stock = SortedStocksList.objects.get(id=obj_id)
    if stock.symbol.has_entry_for_long_short() == stock.entry_type:
        long_short_entry = Indicator.objects.get(name="LONGSHORT")
        long_short, is_created = StrategyTimestamp.objects.get_or_create(indicator=long_short_entry, stock=stock)
        long_short.timestamp = datetime.now()
        long_short.save()
    else:
        StrategyTimestamp.objects.filter(indicator=long_short_entry, stock=stock, timestamp__date=datetime.now().date()).delete()


@celery_app.task(queue="high_priority")
def cache_candles_data(stock_name:str, upstox_user_email="sonupal129@gmail.com", interval:str="1 Minute"):
    try:
        stock = Symbol.objects.get(symbol=stock_name)
    except:
        raise Symbol.DoesNotExist(f"{stock_name} Not Found in Data")
    user = get_upstox_user(email=upstox_user_email)
    user.get_master_contract(stock.exchange.name.upper())
    today_date = get_local_time.date()
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
    for stock in Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True):
        fetch_candles_data.apply_async(kwargs={"symbol":stock, "days":days, "fetch_last_candle":fetch_last_candle_number}) # By Defautl Fetching 5 Minute Candle
    # Now Create Nifty 50 Candle
    fetch_candles_data(symbol="nifty_50", days=days, fetch_last_candle=fetch_last_candle_number)

@celery_app.task(queue="medium_priority")
def delete_last_cached_candles_data():
    for stock in Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True):
        redis_cache.delete(stock)
    redis_cache.delete("nifty_50")
    return "All Cached Candles Deleted Successfully"

@celery_app.task(queue="medium_priority")
def create_stocks_realtime_candle():
    upstox_user = get_upstox_user(email="sonupal129@gmail.com")
    for stock in Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True):
        cache_candles_data.apply_async(kwargs={"stock_name":stock}) #By default one minute is set
    return "All Candles data cached"

@celery_app.task(queue="low_priority")
def create_nifty_50_realtime_candle():
    upstox_user = get_upstox_user(email="sonupal129@gmail.com")
    cache_candles_data.delay(stock_name="nifty_50")
    return f"nifty_50 Data Cached Successfully"


@celery_app.task(queue="low_priority")
def order_on_macd_verification(macd_stamp_id, stochastic_stamp_id): #Need to work more on current entry price
    macd_timestamp = StrategyTimestamp.objects.get(pk=macd_stamp_id)
    stoch_timestamp = StrategyTimestamp.objects.get(pk=stochastic_stamp_id)
    if macd_timestamp.timestamp - stoch_timestamp.timestamp < timedelta(minutes=30):
        stock_current_candle = macd_timestamp.stock.symbol.get_stock_current_candle()
        entry_price = stock_current_candle.get("open_price")
        macd_timestamp.stock.entry_price = entry_price
        macd_timestamp.stock.save()
        slack_message_sender.delay(text=f"{entry_price} Signal {macd_timestamp.stock.entry_type} Stock Name {macd_timestamp.stock.symbol.symbol} Time {macd_timestamp.timestamp.time()}", channel="#random")
        obj = SortedStockDashboardReport.objects.create(name=macd_timestamp.stock.symbol.symbol,
                entry_time=macd_timestamp.timestamp, entry_type=macd_timestamp.stock.entry_type, entry_price=entry_price)


@celery_app.task(queue="high_priority")
def find_update_macd_stochastic_crossover_in_stocks():
    movement_on_entry = {
        "BUY" : 1.2,
        "SELL": -1.2,
    }
    current_time = get_local_time.time()
    start_time = time(9,25)
    if current_time > start_time:
        for stock in redis_cache.get("todays_sorted_stocks"):
            if stock.symbol.is_stock_moved_good_for_trading(movement_percent=movement_on_entry.get(stock.entry_type)):
                # slack_message_sender(text=f"Stock ID {stock.id}")
                get_stochastic_crossover.apply_async(kwargs={"sorted_stock_id": stock.id})
                get_macd_crossover.apply_async(kwargs={"sorted_stock_id": stock.id})
        return "Celery request sent for stock"
    return f"Current time {current_time} not > 9:25"

@celery_app.task(queue="medium_priority")
def todays_movement_stocks_add_on_sideways():
    current_time = get_local_time.time()
    start_time = time(9,25)
    if current_time > start_time:
        add_stock_on_market_sideways.apply_async()
        return "Function Called"
    return "Function Not Called"

# @task(name="testing_function_two")
# def raju_mera_name(run_every=None, run=False):
#     while run:
#         time.sleep(run_every)
#         users = User.objects.all()
#         print(users)
#         print(f"{datetime.now()}")    

# @periodic_task(run_every=(crontab(hour="23-2", minute="1-59/5")), name="testing_function_one")
# def call_function_raju(run=True, run_every=5):
#         users = User.objects.all()
#         print(users)
