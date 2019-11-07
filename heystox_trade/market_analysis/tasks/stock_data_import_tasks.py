from heystox_intraday.intraday_fetchdata import update_all_symbol_candles
from datetime import datetime, timedelta
from django.core.cache import cache
from celery import Celery
from celery.decorators import task, periodic_task
from celery.task.schedules import crontab
from upstox_api.api import *
from django.contrib.auth.models import User
from market_analysis.models import Symbol, MasterContract, Candle
# START CODE BELOW

def update_stocks_data(user_id=1):
    """Update all stocks data after trading day"""
    user = User.objects.get(id=user_id)
    upstox_user = cache.get(user.email, "_upstox_login_user")
    update_symbols_data(upstox_user, "NSE_EQ")

def update_stocks_candle_data(user_id=1):
    """Update all stocks candles data after trading day"""
    user = User.objects.get(id=user_id)
    upstox_user = cache.get(user.email, "_upstox_login_user")
    qs = Symbol.objects.all()
    update_all_symbol_candles(user, upstox_user)

def update_stocks_volume():
    """Update total traded volume in stock"""
    stocks = Symbol.objects.all()
    for stock in stocks:
        volume = Candle.objects.filter(date__contains=datetime.now().date(), symbol=stock).aggregate(Sum("volume"))
        if volume is not None:
            stock.last_day_vtt = volume.get("volume__sum")
            stock.save(update_fields=["last_day_vtt"])

