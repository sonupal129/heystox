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
    return message


@celery_app.task(queue="low_priority")
def unsubscribe_today_trading_stocks():
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks()).values_list("symbol", flat=True)
    message = "Stocks Unsubscribed for Today:\n" + "| ".join(stock.upper() for stock in liquid_stocks)
    slack_message_sender.delay(text=message)
    return message

@celery_app.task(queue="high_priority") 
def todays_movement_stocks_add():
    current_time = get_local_time().time()
    start_time = time(9,20)
    if current_time > start_time:
        add_today_movement_stocks.apply_async()
        return "Function Called"
    return "Function Not Called"


@celery_app.task(queue="high_priority")
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


@celery_app.task(queue="high_priority")
def find_update_macd_stochastic_crossover_in_stocks():
    movement_on_entry = {
        "BUY" : settings.MARKET_BULLISH_MOVEMENT,
        "SELL": settings.MARKET_BEARISH_MOVEMENT,
    }
    current_time = get_local_time().time()
    start_time = time(9,25)
    if current_time > start_time:
        for stock in redis_cache.get("todays_sorted_stocks"):
            if stock.symbol.is_stock_moved_good_for_trading(movement_percent=movement_on_entry.get(stock.entry_type)):
                get_stochastic_crossover.apply_async(kwargs={"sorted_stock_id": stock.id})
                get_macd_crossover.apply_async(kwargs={"sorted_stock_id": stock.id})
        return "Celery request sent for stock"
    return f"Current time {current_time} not > 9:25"

@celery_app.task(queue="medium_priority")
def todays_movement_stocks_add_on_sideways():
    current_time = get_local_time().time()
    start_time = time(9,25)
    if current_time > start_time:
        add_stock_on_market_sideways.apply_async()
        return "Function Called"
    return "Function Not Called"

@celery_app.task(queue="high_priority")
def calculate_profit_loss_on_entry_stocks():
    reports = SortedStockDashboardReport.objects.all()
    if reports:
        for report in reports:
            stock = Symbol.objects.get(symbol=name.lower())
            if stock.get_days_high_low_price(price_type="HIGH") >= report.target_price:
                profit = report.target_price - report.entry_price
                if profit < 0:
                    report.pl = profit - profit * 2
                else:
                    report.pl = profit
                report.save()
            elif stock.get_days_high_low_price(price_type="LOW") <= report.stoploss_price:
                loss = report.stoploss_price - report.entry_price
                if loss > 0:
                    report.pl = loss + loss * 2
                else:
                    report.pl = loss 
                report.save()


# @task(name="testing_function_two")
# def raju_mera_name(run_every=None, run=False):
#     while run:
#         time.sleep(run_every)
#         users = User.objects.all()
#         print(users)
#         print(f"{datetime.now()}")    

