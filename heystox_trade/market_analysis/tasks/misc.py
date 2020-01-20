from market_analysis.models import (Candle, Symbol)
from django.conf import settings
from datetime import datetime, timedelta
from django.db.models import Sum
from django.core.cache import cache, caches
from celery import Celery
from celery.task import periodic_task
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from celery.decorators import task
# Code Starts Below

@periodic_task(run_every=(crontab(day_of_month=1, hour=5, minute=5)),queue="default", options={"queue": "default"})    
def delete_stocks_candles():
    """Delete All candles older more than 30-90 days, currently 32 days"""
    Candle.objects.filter(date__lte=datetime.now().date() - timedelta(32)).delete()
    return "Deleted Successfully"

@periodic_task(run_every=(crontab(day_of_week="2-6", hour=5, minute=55)),queue="default", options={"queue": "default"})    
def clear_all_cache():
    """Delete or clear all cache on daily basis"""
    caches["redis"].clear()
    cache.clear()