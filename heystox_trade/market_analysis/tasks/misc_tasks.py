from market_analysis.models import (Candle, Symbol)
from datetime import datetime, timedelta
from django.core.cache import cache, caches
from celery import shared_task

# Code Starts Below

@shared_task(queue="default")    
def delete_stocks_candles():
    """Delete All candles older more than 30-90 days, currently 32 days"""
    Candle.objects.filter(date__lte=datetime.now().date() - timedelta(32)).delete()
    return "Deleted Successfully"

@shared_task(queue="default")    
def clear_all_cache():
    """Delete or clear all cache on daily basis"""
    caches["redis"].clear()
    cache.clear()