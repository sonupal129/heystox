from heystox_intraday.intraday_fetchdata import update_all_symbol_candles, get_upstox_user, create_symbols_data, get_candles_data
from datetime import datetime, timedelta
from django.core.cache import cache
from celery.task import periodic_task
from celery.schedules import crontab
from upstox_api.api import *
from django.contrib.auth.models import User
from market_analysis.models import Symbol, MasterContract, Candle
from django.db.models import Sum
# START CODE BELOW

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=0)), name="update_all_symbols_price_data")    
def update_stocks_data():
    """Update all stocks data after trading day"""
    upstox_user = get_upstox_user("sonupal129@gmail.com")
    create_symbols_data(upstox_user, "NSE_EQ")

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=17, minute=10)), name="update_all_stocks_candle_data")
def update_stocks_candle_data():
    """Update all stocks candles data after trading day"""
    upstox_user = get_upstox_user("sonupal129@gmail.com")
    qs = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    update_all_symbol_candles(upstox_user, qs)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=20)), name="update_all_stocks_volume")
def update_stocks_volume():
    """Update total traded volume in stock"""
    stocks = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    for stock in stocks:
        volume = Candle.objects.filter(date__contains=datetime.now().date(), symbol=stock).aggregate(Sum("volume"))
        if volume is not None:
            stock.last_day_vtt = volume.get("volume__sum")
            stock.save(update_fields=["last_day_vtt"])

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=4)), name="update_nifty_50_data")
def update_nifty_50_data():
    exchange = MasterContract.objects.get(name="NSE_INDEX")
    stock, is_created = Symbol.objects.get_or_create(symbol="nifty_50", exchange=exchange, name="Nifty 50", isin="000000")
    stock.get_stock_data().delete()
    user = get_upstox_user("sonupal129@gmail.com")
    user.get_master_contract("NSE_INDEX")
    get_candles_data(user, "nifty_50")
    data = user.get_instrument_by_symbol("NSE_INDEX", "nifty_50")
    stock.name = data.name
    stock.last_day_closing_price = data.closing_price
    stock.save()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=23, minute=57)), name="update_symbols_closing_opening_price")
def update_symbols_closing_opening_price():
    """Update all stocks opening and closing price"""
    symbols = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    for symbol in symbols:
        if symbol.get_stock_data():
            symbol.last_day_closing_price = symbol.get_day_closing_price()
            symbol.last_day_opening_price = symbol.get_day_opening_price()
            symbol.save()