from market_analysis.models import (Candle)
from datetime import datetime, timedelta
from django.core.cache import cache
from heystox_trade.celery import app as celery_app

# Code Starts Below

@celery_app.task(queue="low_priority")    
def delete_stocks_candles():
    """Delete All candles older more than 30-90 days, currently 32 days"""
    return Candle.objects.filter(date__lte=datetime.now().date() - timedelta(32)).delete()

# @celery_app.task(queue="low_priority")
# def add_together():
#     return 5+6



