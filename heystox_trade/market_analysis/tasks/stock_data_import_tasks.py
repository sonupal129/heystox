from heystox_intraday.intraday_fetchdata import update_all_symbol_candles
from datetime import datetime, timedelta
from django.core.cache import cache
from celery.task import periodic_task
from celery.schedules import crontab
from upstox_api.api import *
from django.contrib.auth.models import User
from market_analysis.models import Symbol, MasterContract, Candle
# START CODE BELOW

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=22, minute=5)), name="update_all_symbols_price_data")    
def update_stocks_data():
    """Update all stocks data after trading day"""
    user = User.objects.get(email="sonupal129@gmail.com")
    upstox_user = cache.get(user.email, "_upstox_login_user")
    update_symbols_data(upstox_user, "NSE_EQ")

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=22, minute=10)), name="update_all_stocks_candle_data")
def update_stocks_candle_data(user_id=1):
    """Update all stocks candles data after trading day"""
    user = User.objects.get(id=user_id)
    upstox_user = cache.get(user.email, "_upstox_login_user")
    qs = Symbol.objects.all()
    update_all_symbol_candles(upstox_user, qs)

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=23, minute=0)), name="update_all_stocks_volume")
def update_stocks_volume():
    """Update total traded volume in stock"""
    stocks = Symbol.objects.all()
    for stock in stocks:
        volume = Candle.objects.filter(date__contains=datetime.now().date(), symbol=stock).aggregate(Sum("volume"))
        if volume is not None:
            stock.last_day_vtt = volume.get("volume__sum")
            stock.save(update_fields=["last_day_vtt"])

