from market_analysis.models import (Candle, Symbol)
from datetime import datetime, timedelta
from django.db.models import Sum
from heystox_intraday.intraday_fetchdata import update_symbols_data, update_all_symbol_candles
from django.core.cache import cache
from celery import Celery
from celery.decorators import task, periodic_task
from celery.task.schedules import crontab
# Code Starts Below

# @periodic_task(run_every=crontab(minute='*/2'), name="testing_function")
def test_name():
    return "My Name is Sonu"

def delete_stocks_candles():
    Candle.objects.filter(date__lte=datetime.now().date() - timedelta(32)).delete()
    return "Deleted Successfully"

def clear_all_cache():
    cache.clear()

@task(name="sum_two_numbers")
def add(x,y):
    total = x + y
    return total