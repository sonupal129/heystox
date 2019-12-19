from datetime import datetime, timedelta, time
from heystox_intraday.select_stocks_for_trading import (get_liquid_stocks, get_stocks_for_trading,
                                                        get_cached_liquid_stocks, add_today_movement_stocks)
from heystox_intraday.intraday_functions_strategy import (is_stocks_ohl, is_stocks_pdhl, entry_for_long_short, get_macd_crossover,
                                                            get_stochastic_crossover)
from heystox_intraday.intraday_fetchdata import (update_all_symbol_candles, cache_candles_data, get_candles_data)
from django.core.cache import cache, caches
from upstox_api.api import *
from django.contrib.auth.models import User
from celery.task import periodic_task
from celery.schedules import crontab
from market_analysis.models import Candle
from market_analysis.tasks.tasks import slack_message_sender
from celery.decorators import task
from market_analysis.models import (StrategyTimestamp, SortedStocksList, Symbol, UserProfile)
# CODE STARTS BELOW

def function_caller(function, start_time=time(9,15), end_time=time(15,30)):
    """Call function on custom time with interval functionality using celery periodic task"""
    current_time = datetime.now().time()
    if start_time < current_time < end_time:
        function()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=14)), queue = "default", name="subscribe_for_todays_trading_stocks", option={"queue": "default"})
def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = get_cached_liquid_stocks()
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


@periodic_task(run_every=(crontab(day_of_week="1-5", hour=15, minute=45)), queue="default", option={"queue": "default"}, name="unsubscribe_today_trading_stocks")
def unsubscribe_today_trading_stocks():
    liquid_stocks = get_cached_liquid_stocks()
    message = "Stocks Unsubscribed for Today:\n" + "| ".join(stock.symbol.upper() for stock in liquid_stocks)
    slack_message_sender.delay(text=message)
    # upstox_user = get_upstox_user("sonupal129@gmail.com")
    # upstox_user.get_master_contract("NSE_EQ")
    # for stock in liquid_stocks:
    #     upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    # upstox_user.get_master_contract("NSE_INDEX")
    # upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol("NSE_INDEX", "nifty_50"), LiveFeedType.Full)


@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="*/3")),queue="medium", options={"queue": "medium"}, name="add_today_movement_stocks") #Check more for minute how to start-stop after specific time
def todays_movement_stocks_add():
    function_caller(function=add_today_movement_stocks)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="*/6")),queue="medium", options={"queue": "medium"}, name="find_update_ohl_stocks")
def find_ohl_stocks():
    function_caller(function=is_stocks_ohl)

@task(queue="default", name="find_update_pdhl_stocks")
def find_pdhl_stocks(obj_id):
    is_stocks_pdhl(obj_id)

@task(queue="default", name="take_long_short_entry")
def take_entry_for_long_short(obj_id):
    entry_for_long_short(obj_id)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="1-59/5")),queue="medium", options={"queue": "medium"}, name="create_market_hour_candles")
def create_market_hour_candles():
    user = UserProfile.objects.get(user__email="sonupal129@gmail.com")
    upstox_user = user.get_upstox_user()
    liquid_stocks = get_cached_liquid_stocks()
    upstox_user.get_master_contract("NSE_EQ")
    update_all_symbol_candles(user=upstox_user, qs=liquid_stocks, days=0, end_date=datetime.now().date()) # By Defautl Fetching 5 Minute Candle
    # Now Create Nifty 50 Candle 
    upstox_user.get_master_contract("NSE_INDEX")
    get_candles_data(user=upstox_user, symbol="nifty_50", days=0, end_date=datetime.now().date())

@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="1-59/5")),queue="high", options={"queue": "high"}, name="delete_last_cached_candles_data")
def delete_last_cached_candles_data():
    liquid_stocks = get_cached_liquid_stocks()
    redis_cache = caches["redis"]
    for stock in liquid_stocks:
        redis_cache.delete(stock.symbol)
    redis_cache.delete("nifty_50")

def create_stocks_realtime_candle():
    user = UserProfile.objects.get(user__email="sonupal129@gmail.com")
    upstox_user = user.get_upstox_user()
    liquid_stocks = get_cached_liquid_stocks()
    upstox_user.get_master_contract("NSE_EQ")
    for stock in liquid_stocks:
        cache_candles_data(upstox_user, stock)

def create_nifty_50_realtime_candle():
    user = UserProfile.objects.get(user__email="sonupal129@gmail.com")
    upstox_user = user.get_upstox_user()
    nifty_50 = Symbol.objects.get(symbol="nifty_50")
    upstox_user.get_master_contract("NSE_INDEX")
    cache_candles_data(upstox_user, nifty_50)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="*/1")),queue="high", options={"queue": "high"}, name="create_stocks_realtime_candle_fuction_caller")
def create_stocks_realtime_candle_fuction_caller():
    start_time = time(9,15)
    end_time = time(15,35)
    # Now Call Nifty 50 Function to Create Candle
    function_caller(create_nifty_50_realtime_candle, start_time, end_time)
    # Now Call Rest of Stocks Function to Create Candle
    function_caller(create_stocks_realtime_candle, start_time, end_time)


# @task(name="delete_cached_ticker_and_create_candle")
# def delete_cached_tickerdata_and_create_candle():
#     """This function will delete all stocks cached tickerdata and create candle on every 4:59 minute """
#     liquid_stocks = get_cached_liquid_stocks()
#     redis_cache = caches["redis"]
#     candle_to_create = []
#     for stock in liquid_stocks:
#         try:
#             data = get_stock_current_candle(stock.symbol.upper())
#             data["symbol_id"] = stock.id
#             candle_to_create.append(Candle(**data))
#             redis_cache.delete(stock.symbol.upper())
#         except:
#             continue
#     Candle.objects.bulk_create(candle_to_create)

# @periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="*/5")), name="create_candles_and_delete_ticker")
# def create_candles_and_delete_ticker():
#     function_caller(9,20,15,35,delete_cached_tickerdata_and_create_candle)

@task(name="place_order_on_macd_verification")
def order_on_macd_verification(macd_stamp_id, stochastic_stamp_id): #Need to work more on current entry price
    macd = StrategyTimestamp.objects.get(pk=macd_stamp_id)
    stoch = StrategyTimestamp.objects.get(pk=stochastic_stamp_id)
    if macd.timestamp - stoch.timestamp < timedelta(minutes=20):
        entry_price = get_stock_current_candle(macd.stock.symbol.symbol.upper()).open_price
        macd.stock.entry_price = entry_price
        macd.stock.save()
        send_slack_message(text=f"{entry_price} Signal {macd.stock.entry_type} Stock Name {macd.stock.symbol.symbol}")

def find_update_macd_crossover_in_stocks():
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    stocks  = None
    if nifty_50 == "BUY":
        stocks = SortedStocksList.objects.filter(entry_type="BUY", created_at=datetime.now().date())
    elif nifty_50 == "SELL":
        stocks = SortedStocksList.objects.filter(entry_type="SELL", created_at=datetime.now().date())
    if stocks:
        for stock in stocks:
            if stock.entry_type == "BUY" and stock.symbol.get_stock_movement() >= 1.2:
                get_macd_crossover(stock)
            elif stock.entry_type == "SELL" and stock.get_stock_movement() <= -1.2:
                get_macd_crossover(stock)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="*/1")),queue="medium", options={"medium": "default"}, name="macd_crossover_finder")
def find_macd_crossovers():
    function_caller(function=find_update_macd_crossover_in_stocks)

def find_update_stochastic_crossover_in_stocks():
    nifty_50 = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
    stocks  = None
    if nifty_50 == "BUY":
        stocks = SortedStocksList.objects.filter(entry_type="BUY", created_at=datetime.now().date())
    elif nifty_50 == "SELL":
        stocks = SortedStocksList.objects.filter(entry_type="SELL", created_at=datetime.now().date())
    if stocks:
        for stock in stocks:
            if stock.entry_type == "BUY" and stock.symbol.get_stock_movement() >= 1.2:
                get_stochastic_crossover(stock)
            elif stock.entry_type == "SELL" and stock.get_stock_movement() <= -1.2:
                get_stochastic_crossover(stock)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-15", minute="*/1")),queue="medium", options={"queue": "medium"}, name="stochastic_crossover_finder")
def find_stochastic_crossovers():
    function_caller(function=find_update_stochastic_crossover_in_stocks)



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
