from datetime import datetime
from heystox_intraday.select_stocks_for_trading import get_liquid_stocks, get_stocks_for_trading
from django.core.cache import cache
from upstox_api.api import *
from django.contrib.auth.models import User
from celery.task import periodic_task
from celery.schedules import crontab
# CODE STARTS BELOW

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=13)), name="cache_liquid_stocks_for_today")
def cache_today_liquid_stocks():
    """Cache todays liquid stock so no need to call database"""
    cache.set(datetime.now() + "_today_liquid_stocks", get_liquid_stocks())


# Need to Work more on this function
def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = cache.get(datetime.now() + "_today_liquid_stocks")
    user = User.objects.get(email="sonupal129@gmail.com")
    upstox_user = cache.get(user.email + "_upstox_login_user")
    def event_handler_quote_update(message):
        print("Quote Update: %s" % str(message))
    upstox_user.set_on_quote_update(event_handler_quote_update) # Should Send a slack message instead of this
    for stock in liquid_stocks:
        upstox_user.subscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    u.start_websocket(True)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=15, minute=45)), name="unsubscribe_today_trading_stocks")
def unsubscribe_today_trading_stocks():
    liquid_stocks = cache.get(datetime.now() + "_today_liquid_stocks")
    user = User.objects.get(email="sonupal129@gmail.com")
    upstox_user = cache.get(user.email + "_upstox_login_user")
    for stock in liquid_stocks:
        upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)

# def get_today_movement_stocks():


@periodic_task(run_every=(crontab(minute='*/1')), name="testing_function_one")
def test_name_chutiya():
    users = User.objects.all()
    print(users)



