from market_analysis.models import (Candle)
from market_analysis.imports import *

# Code Starts Below

@celery_app.task(queue="low_priority")    
def delete_stocks_candles():
    """Delete All candles older more than 30-90 days, currently 32 days"""
    return Candle.objects.filter(date__lte=get_local_time.date() - timedelta(32)).delete()

# @celery_app.task(queue="low_priority")
# def add_together():
#     return 5+6



