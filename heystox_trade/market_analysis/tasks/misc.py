from market_analysis.models import (Candle, Symbol)
from django.conf import settings
from datetime import datetime, timedelta
from django.db.models import Sum
from heystox_intraday.intraday_fetchdata import update_symbols_data, update_all_symbol_candles
from django.core.cache import cache
from celery import Celery
from celery.task import periodic_task
from celery.schedules import crontab
from celery.utils.log import get_task_logger
# Code Starts Below

@periodic_task(run_every=(crontab(day_of_month=1, hour=1, minute=7)), name="delete_old_candles_upto_30_days")    
def delete_stocks_candles():
    """Delete All candles older more than 30-90 days, currently 32 days"""
    Candle.objects.filter(date__lte=datetime.now().date() - timedelta(32)).delete()
    return "Deleted Successfully"

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=5, minute=55)), name="clear_all_cache")    
def clear_all_cache():
    """Delete or clear all cache on daily basis"""
    cache.clear()