from heystox_intraday.intraday_fetchdata import update_all_symbol_candles, create_symbols_data, get_candles_data, get_upstox_user
from datetime import datetime, timedelta
from django.core.cache import cache
from celery.task import periodic_task
from celery.schedules import crontab
from upstox_api.api import *
from django.contrib.auth.models import User
from market_analysis.models import Symbol, MasterContract, Candle
from django.db.models import Sum
from heystox_intraday.intraday_fetchdata import get_upstox_user
from .day_trading_tasks import fetch_candles_data
import requests
from django.conf import settings
# START CODE BELOW

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=0)),queue="default", options={"queue": "default"})    
def update_stocks_data():
    """Update all stocks data after trading day"""
    create_symbols_data(index="NSE_EQ")
    return "All Stocks Data Updated Succefully"

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=17, minute=10)),queue="default", options={"queue": "default"})
def update_stocks_candle_data(days=0):
    """Update all stocks candles data after trading day"""
    qs = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    for q in qs:
        fetch_candles_data.delay(q.symbol, days)
    return "All Stocks Candle Data Imported Successfully"


@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=20)),queue="default", options={"queue": "default"})
def update_stocks_volume():
    """Update total traded volume in stock"""
    stocks = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    for stock in stocks:
        volume = stock.get_stock_data().aggregate(Sum("volume"))
        if volume.get("volume__sum"):
            stock.last_day_vtt = volume.get("volume__sum")
            stock.save(update_fields=["last_day_vtt"])
    return "All Stocks Volume Updated"

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=19, minute=22)),queue="default", options={"queue": "default"})
def update_nifty_50_data(days=0):
    exchange = MasterContract.objects.get(name="NSE_INDEX")
    stock, is_created = Symbol.objects.get_or_create(symbol="nifty_50", exchange=exchange)
    get_candles_data(symbol="nifty_50", days=days)
    todays_candles = stock.get_stock_data(days=0)
    if todays_candles:
        stock.last_day_closing_price = stock.get_day_closing_price()
        stock.last_day_opening_price = stock.get_day_opening_price()
        stock.save()
        return "Updated Nifty_50 Data"

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=23, minute=55)),queue="default", options={"queue": "default"})
def update_symbols_closing_opening_price():
    """Update all stocks opening and closing price"""
    symbols = Symbol.objects.exclude(exchange__name="NSE_INDEX")
    updated_stocks = []
    for symbol in symbols:
        if symbol.get_stock_data(days=0):
            symbol.last_day_closing_price = symbol.get_day_closing_price()
            symbol.last_day_opening_price = symbol.get_day_opening_price()
            symbol.save()
            updated_stocks.append(symbol.id)
    return "Updated Symbols Closing Price"

# @periodic_task(run_every=(crontab(day_of_week="1-5", hour=9, minute=9)),queue="default", options={"queue": "default"})
# def import_premarket_stocks_data():
#     urls = {"NFTY": "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/nifty.json",
#             "NFTYBNK": "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/niftybank.json"}
#     for sector, url in urls.items():
#         response = requests.get(url, headers=settings.NSE_HEADERS)
#         if response.status_code == 200:
#             response_data = response.json().get("data")
#             bulk_data_upload = []
#             if response_data:
#                 for data in response_data:
#                     context = {}
#                     symbol = Symbol.objects.get_or_create(symbol=data.get("symbol"), created_at__date=datetime.now().date())
#                     symbol.sector = sector
#                     symbol.price = float(data.get("iep"))
#                     symbol.change = float(data.get("chn"))
#                     symbol.previous_close = float(data.get("pCls"))

# def import_daily_losers_gainers():
#     urls = {
#         "BUY": ["https://www1.nseindia.com/live_market/dynaContent/live_analysis/gainers/niftyGainers1.json",
#                 "https://www1.nseindia.com/live_market/dynaContent/live_analysis/gainers/jrNiftyGainers1.json"],
#         "SELL": ["https://www1.nseindia.com/live_market/dynaContent/live_analysis/losers/niftyLosers1.json",
#                 "https://www1.nseindia.com/live_market/dynaContent/live_analysis/losers/jrNiftyLosers1.json"]
#     }
#     nifty_movement = Symbol.objects.get(symbol="nifty_50").get_nifty_movement()
#     def func(obj):
#         open_price = float(obj.get("openPrice"))
#         change = float(obj.get("netPrice"))
#         if open_price >= 100 and open_price <= 300 and change >= 1.2:
#             return obj
#     if nifty_movement in ("BUY", "SELL"):
#         import_urls = urls.get(nifty_movement, None)
#         if import_urls:
#             for url in import_urls:
#                 response = requests.get(url, headers=settings.NSE_HEADERS)
#                 if response.status_code == 200:
#                     response = filter(key=func, response)
#                     print(list(response))

