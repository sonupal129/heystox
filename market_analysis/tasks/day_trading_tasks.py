from .stock_data_import_tasks import (fetch_candles_data)
from .notification_tasks import slack_message_sender
from market_analysis.models import (StrategyTimestamp, SortedStocksList, Symbol, UserProfile, Candle, Indicator, SortedStockDashboardReport)
from .trading import *
from market_analysis.imports import *
from .intraday_indicator import get_macd_crossover, get_stochastic_crossover
from .upstox_events_handlers import *
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

@celery_app.task(queue="high_priority") # Need to work more on this function giving wrong data
def calculate_profit_loss_on_entry_stocks():
    todays_date = get_local_time().date()
    reports = SortedStockDashboardReport.objects.filter(entry_time__date=todays_date)
    if reports:
        for report in reports:
            stock = Symbol.objects.get(symbol=report.name.lower())
            live_data = stock.get_stock_live_data()
            live_data = live_data.loc[live_data["date"] > str(report.entry_time)]
            if report.entry_type == "BUY":
                target_price = live_data.loc[live_data["high_price"] >= report.target_price ].iloc[0]
                stoploss_price = live_data.loc[live_data["low_price"] <= report.stoploss_price ].iloc[0]
            elif report.entry_type == "SELL":
                target_price = live_data.loc[live_data["low_price"] <= report.target_price ].iloc[0]
                stoploss_price = live_data.loc[live_data["high_price"] >= report.stoploss_price ].iloc[0]
            earliest_time = min(target_price.date, stoploss_price.date)
            if target_price.date == earliest_time:
                status = "TARGET_HIT"
            elif stoploss_price.date == earliest_time:
                status = "STOPLOSS_HIT"
            if status == "STOPLOSS_HIT":
                report.pl = round(abs(report.entry_price - report.stoploss_price), 2)
            elif status == "STATUS":
                report.pl = round(abs(report.target_price - report.entry_price), 2)
            report.save()


@celery_app.task(queue="high_priority")
def start_upstox_websocket(run_in_background=True):
    user = get_upstox_user()
    user.set_on_quote_update(event_handler_on_quote_update)
    user.set_on_trade_update(event_handler_on_trade_update)
    user.set_on_order_update(event_handler_on_order_update)
    user.set_on_disconnect(event_handler_on_disconnection)
    user.set_on_error(event_handler_on_error)
    user.start_websocket(run_in_background)
    slack_message_sender.delay(text="Websocket for Live Data Feed Started")
    return "Websocket Started"

