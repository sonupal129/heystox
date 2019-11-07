import slack
from market_analysis.models import (Candle, Symbol)
from django.conf import settings
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

def send_slack_message(channel='#heystox', text='Message', attachments=None):
    client = slack.WebClient(token=settings.SLACK_TOKEN)
    response = client.chat_postMessage(
        channel=channel,
        text=text,
        attachments=attachments
    )
    return response.get('ok', False)


@task(name="sum_two_numbers")
def add(x,y):
    total = x + y
    return total