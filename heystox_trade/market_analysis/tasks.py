import slack
from datetime import datetime, timedelta
from django.db.models import Sum
from django.core.cache import cache
from django.conf import settings
from celery import Celery, shared_task
from celery.decorators import task
from market_analysis.models import (Candle, Symbol)
# from heystox_intraday.intraday_fetchdata import update_symbol_data, update_all_symbol_candles
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

def send_slack_message(channel='#heystox', text='Message', attachments=None):
    client = slack.WebClient(token=settings.SLACK_TOKEN)
    response = client.chat_postMessage(
        channel=channel,
        text=text,
        attachments=attachments
    )
    return response.get('ok', False)


@task
def add(x,y):
    total = x + y
    return total
# app = Celery('tasks', broker='redis://localhost')
