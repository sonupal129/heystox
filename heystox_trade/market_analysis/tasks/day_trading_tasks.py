from datetime import datetime
from heystox_intraday.select_stocks_for_trading import get_liquid_stocks, get_stocks_for_trading
from django.core.cache import cache
from upstox_api.api import *
from django.contrib.auth.models import User
# CODE STARTS BELOW

def cache_today_liquid_stocks():
    """Cache todays liquid stock so no need to call database"""
    cache.set(datetime.now() + "_today_liquid_stocks", get_liquid_stocks())

def subscribe_today_trading_stocks():
    """Fetch todays liquid stocks from cache then register those stock for live feed"""
    liquid_stocks = cache.get(datetime.now() + "_today_liquid_stocks")
    user = User.objects.first()
    upstox_user = cache.get(user.email + "_upstox_login_user")
    def event_handler_quote_update(message):
        print("Quote Update: %s" % str(message))
    upstox_user.set_on_quote_update(event_handler_quote_update) # Should Send a slack message instead of this
    for stock in liquid_stocks:
        upstox_user.subscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    u.start_websocket(True)

def unsubscribe_today_trading_stocks():
    liquid_stocks = cache.get(datetime.now() + "_today_liquid_stocks")
    user = User.objects.first()
    upstox_user = cache.get(user.email + "_upstox_login_user")
    for stock in liquid_stocks:
        upstox_user.unsubscribe(upstox_user.get_instrument_by_symbol(stock.exchange.name, stock.symbol), LiveFeedType.Full)
    upstox_user.stop_websocket(True)

# def get_today_movement_stocks():



