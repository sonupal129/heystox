from heystox_intraday.intraday_fetchdata import update_all_symbol_candles, create_symbols_data, get_candles_data
from datetime import datetime, timedelta
from django.core.cache import cache
from celery.task import periodic_task
from celery.schedules import crontab
from upstox_api.api import *
from django.contrib.auth.models import User
from market_analysis.models import Symbol, MasterContract, Candle, UserProfile
from django.db.models import Sum
# START CODE BELOW

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=0)),queue="default", options={"queue": "default"}, name="update_all_symbols_price_data")    
def update_stocks_data():
    """Update all stocks data after trading day"""
    user = UserProfile.objects.get(user__email="sonupal129@gmail.com")
    upstox_user = user.get_upstox_user()
    create_symbols_data(upstox_user, "NSE_EQ")
    return "All Stocks Data Updated Succefully"

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=17, minute=10)),queue="default", options={"queue": "default"}, name="update_all_stocks_candle_data")
def update_stocks_candle_data(days=0):
    """Update all stocks candles data after trading day"""
    user = UserProfile.objects.get(user__email="sonupal129@gmail.com")
    upstox_user = user.get_upstox_user()
    qs = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    upstox_user.get_master_contract("NSE_EQ")
    update_all_symbol_candles(user=upstox_user, qs=qs, days=days)
    return "All Stocks Candle Data Imported Successfully"


@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=20)),queue="default", options={"queue": "default"}, name="update_all_stocks_volume")
def update_stocks_volume():
    """Update total traded volume in stock"""
    stocks = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    for stock in stocks:
        volume = stock.get_stock_data().aggregate(Sum("volume"))
        if volume is not None:
            stock.last_day_vtt = volume.get("volume__sum")
            stock.save(update_fields=["last_day_vtt"])
    return "All Stocks Volume Updated"

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=22)),queue="default", options={"queue": "default"}, name="update_nifty_50_data")
def update_nifty_50_data(days=0):
    exchange = MasterContract.objects.get(name="NSE_INDEX")
    stock, is_created = Symbol.objects.get_or_create(symbol="nifty_50", exchange=exchange)
    user = UserProfile.objects.get(user__email="sonupal129@gmail.com")
    upstox_user = user.get_upstox_user()
    upstox_user.get_master_contract("NSE_INDEX")
    get_candles_data(user=upstox_user, symbol="nifty_50", days=days)
    todays_candles = stock.get_stock_data()
    if todays_candles:
        stock.last_day_closing_price = todays_candles.last().close_price
        stock.last_day_opening_price = todays_candles.last().open_price
        stock.save()
        return "Updated Nifty_50 Data"

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=10)),queue="default", options={"queue": "default"}, name="update_symbols_closing_opening_price")
def update_symbols_closing_opening_price():
    """Update all stocks opening and closing price"""
    symbols = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    updated_stocks = []
    for symbol in symbols:
        if symbol.get_stock_data():
            symbol.last_day_closing_price = symbol.get_day_closing_price()
            symbol.last_day_opening_price = symbol.get_day_opening_price()
            symbol.save()
            updated_stocks.append(symbol.id)
    symbols.exclude(id__in=updated_stocks).delete()
    return "Updated Symbols Closing Price"