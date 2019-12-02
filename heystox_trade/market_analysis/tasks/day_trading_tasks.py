from datetime import datetime, timedelta
from heystox_intraday.select_stocks_for_trading import (get_liquid_stocks, get_stocks_for_trading, get_nifty_movement,
                                                        get_cached_liquid_stocks, add_today_movement_stocks)
from heystox_intraday.intraday_functions_strategy import (is_stocks_ohl, is_stocks_pdhl, entry_for_long_short, get_macd_crossover,
                                                            get_stochastic_crossover)
from heystox_intraday.intraday_fetchdata import (get_stock_current_candle, get_upstox_user)
from django.core.cache import cache, caches
from upstox_api.api import *
from django.contrib.auth.models import User
from celery.task import periodic_task
from celery.schedules import crontab
from heystox_intraday.intraday_fetchdata import parse_stock_response_data
from market_analysis.models import Candle

from celery.decorators import task
from market_analysis.models import (StrategyTimestamp, SortedStocksList)
import time
# CODE STARTS BELOW

def function_caller(start_hour, start_minute, end_hour, end_minute, func, *args, **kwargs):
    """Call function on custom time with interval functionality using celery periodic task"""
    current_time = datetime.now()
    if current_time.hour >= start_hour and current_time.minute >= start_minute and current_time.hour <= end_hour and current_time.minute <= end_minute:
        func.delay(*args, **kwargs)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=14)), name="subscribe_for_todays_trading_stocks")
def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = get_cached_liquid_stocks()
    upstox_user = get_upstox_user("sonupal129@gmail.com")
    upstox_user.set_on_quote_update(parse_stock_response_data)
    upstox_user.get_master_contract("NSE_EQ")
    for stock in liquid_stocks:
        upstox_user.subscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    upstox_user.get_master_contract("NSE_INDEX")
    upstox_user.subscribe(upstox_user.get_instrument_by_symbol("NSE_INDEX", "nifty_50"), LiveFeedType.Full)
    upstox_user.start_websocket(True)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=15, minute=45)), name="unsubscribe_today_trading_stocks")
def unsubscribe_today_trading_stocks():
    liquid_stocks = get_cached_liquid_stocks()
    upstox_user = get_upstox_user("sonupal129@gmail.com")
    for stock in liquid_stocks:
        upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol("NSE_INDEX", "nifty_50"), LiveFeedType.Full)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour='9-16', minute='*/3')), name="add_today_movement_stocks") #Check more for minute how to start-stop after specific time
def todays_movement_stocks_add():
    function_caller(9,30,15,30, add_today_movement_stocks)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour='9-16', minute='*/6')), name="find_update_ohl_stocks")
def find_ohl_stocks():
    function_caller(9,30,15,30, is_stocks_ohl)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=45)), name="find_update_pdhl_stocks")
def find_pdhl_stocks():
    is_stocks_pdhl()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=46)), name="take_long_short_entry")
def take_entry_for_long_short():
    entry_for_long_short()

@task(name="delete_cached_ticker_and_create_candle")
def delete_cached_tickerdata_and_create_candle():
    """This function will delete all stocks cached tickerdata and create candle on every 4:59 minute """
    liquid_stocks = get_cached_liquid_stocks()
    redis_cache = caches["redis"]
    candle_to_create = []
    for stock in liquid_stocks:
        try:
            candle_to_create.append(Candle(**get_stock_current_candle(stock.symbol)))
            redis_cache.delete(stock.symbol)
        except:
            continue
    Candle.objects.bulk_create(candle_to_create)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour="9-16", minute="*/5")), name="create_candles_and_delete_ticker")
def create_candles_and_delete_ticker():
    function_caller(9,20,15,35,delete_cached_tickerdata_and_create_candle)

@task(name="place_order_on_macd_verification")
def order_on_macd_verification(macd_stamp_id, stochastic_stamp_id): #Need to work more on current entry price
    macd = StrategyTimestamp.objects.get(pk=macd_stamp_id)
    stoch = StrategyTimestamp.objects.get(pk=stochastic_stamp_id)
    if macd.timestamp - stoch.timestamp < timedelta(minutes=20):
        entry_price = get_stock_current_candle(macd.stock.symbol.name).open_price
        macd.stock.entry_price = entry_price
        macd.stock.save()
        send_slack_message(text=f"{entry_price} Signal {macd.stock.entry_type}")

@task(name="macd_finder")
def find_update_macd_crossover_in_stocks():
    nifty_50 = get_nifty_movement(date=datetime.now())
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

@periodic_task(run_every=timedelta(seconds=40), name="macd_crossover_finder")
def find_macd_crossovers():
    function_caller(9,30,15,30,find_update_macd_crossover_in_stocks)

@task(name="stochastic_finder")
def find_update_stochastic_crossover_in_stocks():
    nifty_50 = get_nifty_movement(date=datetime.now())
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

@periodic_task(run_every=timedelta(seconds=25), name="stochastic_crossover_finder")
def find_macd_crossovers():
    function_caller(9,30,15,30,find_update_stochastic_crossover_in_stocks)

# @periodic_task(run_every=(crontab(minute="*/1")), name="testing_function_one")
# def raju_mera_name():
#     users = User.objects.all()
#     print(users)
#     print(f"{datetime.now()}")

# @periodic_task(run_every=(crontab(minute='*/1')), name="testing_function_one")
# def test_name_chutiya():
    # print(function_caller(12,46,12,52,raju_mera_name))
    

