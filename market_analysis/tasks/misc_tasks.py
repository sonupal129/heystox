from market_analysis.models import (Candle)
from datetime import datetime, timedelta
from django.core.cache import cache, caches
from heystox_trade.celery import app as celery_app

# Code Starts Below

@celery_app.task(queue="low_priority")    
def delete_stocks_candles():
    """Delete All candles older more than 30-90 days, currently 32 days"""
    return Candle.objects.filter(date__lte=datetime.now().date() - timedelta(32)).delete()

@celery_app.task(queue="low_priority") 
def clear_all_cache():
    """Delete or clear all cache on daily basis"""
    caches["redis"].clear()
    cache.clear()

# @celery_app.task(queue="low_priority")
# def add_together():
#     return 5+6



