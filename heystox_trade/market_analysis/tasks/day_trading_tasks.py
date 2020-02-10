from datetime import datetime, timedelta, time
from market_analysis.heystox_intraday.select_stocks_for_trading import (get_liquid_stocks, get_stocks_for_trading, add_stock_on_market_sideways,
                                                        get_cached_liquid_stocks, add_today_movement_stocks)
from market_analysis.heystox_intraday.intraday_functions_strategy import (is_stocks_ohl, is_stocks_pdhl, entry_for_long_short, get_macd_crossover,
                                                            get_stochastic_crossover)
from market_analysis.heystox_intraday.intraday_fetchdata import (update_all_symbol_candles, cache_candles_data, get_candles_data, get_upstox_user)
from django.core.cache import cache, caches
from upstox_api.api import *
from django.contrib.auth.models import User
from .tasks import slack_message_sender
from market_analysis.models import (StrategyTimestamp, SortedStocksList, Symbol, UserProfile, Candle)
from celery import shared_task


# CODE STARTS BELOW

def function_caller(function, start_hour:int=9, start_minute:int=15, end_hour:int=15, end_minute:int=30):
    """Call function on custom time with interval functionality using celery periodic task"""
    start_time = time(start_hour, start_minute)
    end_time = time(end_hour, end_minute)
    current_time = datetime.now().time()
    if current_time >= start_time and current_time <= end_time:
        function()

@shared_task(queue="default")
def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    message = "Today's Subscribed Stocks:\n" + "| ".join(stock.symbol.upper() for stock in liquid_stocks)
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


@shared_task(queue="default")
def unsubscribe_today_trading_stocks():
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    message = "Stocks Unsubscribed for Today:\n" + "| ".join(stock.symbol.upper() for stock in liquid_stocks)
    slack_message_sender.delay(text=message)
    # upstox_user = get_upstox_user("sonupal129@gmail.com")
    # upstox_user.get_master_contract("NSE_EQ")
    # for stock in liquid_stocks:
    #     upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    # upstox_user.get_master_contract("NSE_INDEX")
    # upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol("NSE_INDEX", "nifty_50"), LiveFeedType.Full)
    return message

@shared_task(queue="medium") #Check more for minute how to start-stop after specific time
def todays_movement_stocks_add():
    current_time = datetime.now().time()
    start_time = time(9,25)
    if current_time > start_time:
        add_today_movement_stocks()
        return "Function Called"
    return "Function Not Called"

@shared_task(queue="medium")
def find_ohl_stocks():
    current_time = datetime.now().time()
    start_time = time(9,25)
    if current_time > start_time:
        is_stocks_ohl()
        return "Function Called"
    return "Function Not Called"

@shared_task(queue="default")
def find_pdhl_stocks(obj_id):
    is_stocks_pdhl(obj_id)

@shared_task(queue="default")
def take_entry_for_long_short(obj_id):
    entry_for_long_short(obj_id)

@shared_task(queue="high")
def candle_data_cache(stock_name):
    return cache_candles_data(stock_name)

@shared_task(queue="medium")
def fetch_candles_data(stock_name, days):
    return get_candles_data(symbol=stock_name, days=days)
    
@shared_task(queue="medium")
def create_market_hour_candles():
    upstox_user = get_upstox_user(email="sonupal129@gmail.com")
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    for stock in liquid_stocks:
        fetch_candles_data.delay(stock.symbol, 0) # By Defautl Fetching 5 Minute Candle
    # Now Create Nifty 50 Candle
    get_candles_data(symbol="nifty_50", days=0)

@shared_task(queue="high")
def delete_last_cached_candles_data():
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    redis_cache = cache
    for stock in liquid_stocks:
        redis_cache.delete(stock.symbol)
    redis_cache.delete("nifty_50")
    return "All Cached Candles Deleted Successfully"

@shared_task(queue="medium")
def create_stocks_realtime_candle():
    upstox_user = get_upstox_user(email="sonupal129@gmail.com")
    liquid_stocks = Symbol.objects.filter(id__in=get_cached_liquid_stocks())
    # upstox_user.get_master_contract("NSE_EQ")
    for stock in liquid_stocks:
        candle_data_cache.delay(stock_name=stock.symbol) #By default one minute is set
    return "All Candles data cached"

@shared_task(queue="medium")
def create_nifty_50_realtime_candle():
    upstox_user = get_upstox_user(email="sonupal129@gmail.com")
    # upstox_user.get_master_contract("NSE_INDEX")
    candle_data_cache.delay(stock_name="nifty_50")
    return f"nifty_50 Data Cached Successfully"

@shared_task(queue="high")
def create_stocks_realtime_candle_fuction_caller():
    # Now Call Nifty 50 Function to Create Candle
    create_nifty_50_realtime_candle()
    # Now Call Rest of Stocks Function to Create Candle
    create_stocks_realtime_candle()
    return "All Data Cached"


@shared_task(queue="default")
def order_on_macd_verification(macd_stamp_id, stochastic_stamp_id): #Need to work more on current entry price
    macd_timestamp = StrategyTimestamp.objects.get(pk=macd_stamp_id)
    stoch_timestamp = StrategyTimestamp.objects.get(pk=stochastic_stamp_id)
    if macd_timestamp.timestamp - stoch_timestamp.timestamp < timedelta(minutes=30):
        stock_current_candle = macd_timestamp.stock.symbol.get_stock_current_candle()
        entry_price = stock_current_candle.get("open_price")
        macd_timestamp.stock.entry_price = entry_price
        macd_timestamp.stock.save()
        slack_message_sender.delay(text=f"{entry_price} Signal {macd.stock.entry_type} Stock Name {macd.stock.symbol.symbol}", channel="#random")


@shared_task(queue="high")
def check_macd_crossover(stock_id):
    return get_macd_crossover(stock_id)


@shared_task(queue="high")
def check_stochastic_crossover(stock_id):
    return get_stochastic_crossover(stock_id)


@shared_task(queue="default")
def find_update_macd_stochastic_crossover_in_stocks():
    stocks = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
    if stocks:
        for stock in stocks:
            if (stock.symbol.is_stock_moved_good_for_trading(movement_percent=-1.2), stock.symbol.is_stock_moved_good_for_trading(movement_percent=1.2)):
                slack_message_sender(text=f"Stock ID {stock.id}")
                check_stochastic_crossover.s(stock.id)
                check_macd_crossover.s(stock.id)

@shared_task(queue="medium")
def todays_movement_stocks_add_on_sideways():
    current_time = datetime.now().time()
    start_time = time(9,25)
    if current_time > start_time:
        add_stock_on_market_sideways()
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