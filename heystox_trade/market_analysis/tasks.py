from market_analysis.models import (Candle, Symbol)
from datetime import datetime, timedelta
from django.db.models import Sum
from heystox_intraday.intraday_fetchdata import update_symbol_data, update_all_symbol_candles
from django.core.cache import cache
# Code Starts Below


def update_stocks_volume():
    """Update total traded volume in stock"""
    stocks = Symbol.objects.all()
    for stock in stocks:
        volume = Candle.objects.filter(date__contains=datetime.now().date(), symbol=stock).aggregate(Sum("volume"))
        if volume is not None:
            stock.last_day_vtt = volume.get("volume__sum")
            stock.save(update_fields=["last_day_vtt"])

def update_stocks_data():
    """Update all stocks data after trading day"""
    user = cache.get("upstox_login_user")
    update_symbol_data(user, "NSE_EQ")

def update_stocks_candle_data():
    user = cache.get("upstox_login_user")
    qs = Symbol.objects.all()
    update_all_symbol_candles(user, qs)

def delete_stocks_candles():
    Candle.objects.filter(date__lte=datetime.now().date() - timedelta(32)).delete()
    return "Deleted Successfully"

def clear_all_cache():
    cache.clear()

    



