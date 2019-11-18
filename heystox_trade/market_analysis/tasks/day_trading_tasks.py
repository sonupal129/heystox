from datetime import datetime
from heystox_intraday.select_stocks_for_trading import (get_liquid_stocks, get_stocks_for_trading, 
                                                        get_cached_liquid_stocks, add_today_movement_stocks)
from heystox_intraday.intraday_functions_strategy import (is_stocks_ohl, is_stocks_pdhl, entry_for_long_short)
from django.core.cache import cache
from upstox_api.api import *
from django.contrib.auth.models import User
from celery.task import periodic_task
from celery.schedules import crontab
from heystox_intraday.intraday_fetchdata import parse_stock_response_data
# CODE STARTS BELOW

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=13)), name="cache_liquid_stocks_for_today")
def cache_today_liquid_stocks():
    """Cache todays liquid stock so no need to call database"""
    cache.set(str(datetime.now().date()) + "_today_liquid_stocks", get_liquid_stocks())

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=14)), name="subscribe_for_todays_trading_stocks")
def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = get_cached_liquid_stocks()
    user = User.objects.get(email="sonupal129@gmail.com")
    upstox_user = cache.get(user.email + "_upstox_login_user")
    upstox_user.set_on_quote_update(parse_stock_response_data) # Should Send a slack message instead of this
    for stock in liquid_stocks:
        upstox_user.subscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    upstox_user.start_websocket(True)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=15, minute=45)), name="unsubscribe_today_trading_stocks")
def unsubscribe_today_trading_stocks():
    liquid_stocks = get_cached_liquid_stocks()
    user = User.objects.get(email="sonupal129@gmail.com")
    upstox_user = cache.get(user.email + "_upstox_login_user")
    for stock in liquid_stocks:
        upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour='9-15', minute='*/3')), name="add_today_movement_stocks") #Check more for minute how to start-stop after specific time
def todays_movement_stocks_add():
    add_today_movement_stocks()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour='9-15', minute='*/3')), name="find_update_ohl_stocks")
def find_ohl_stocks():
    is_stocks_ohl()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=45)), name="find_update_pdhl_stocks")
def find_pdhl_stocks():
    is_stocks_pdhl()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=46)), name="take_long_short_entry")
def take_entry_for_long_short():
    entry_for_long_short()


@periodic_task(run_every=(crontab(minute='*/1')), name="testing_function_one")
def test_name_chutiya():
    users = User.objects.all()
    print(users)



