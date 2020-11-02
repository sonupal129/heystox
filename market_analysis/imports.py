# Django Date Time
from datetime import datetime, timedelta, date, time
import pytz
from time import sleep
import time as time_library
# Project Settings 
from django.conf import settings

# PSQL Fields
from django.contrib.postgres.fields import JSONField

# Pandas, Numpy & Data Science Libraries
import pandas as pd
import numpy as np

# Python Libraries
import csv, random, string

# TA LIbrary for Stock Market
from ta.trend import macd, macd_diff, macd_signal, ema, ema_indicator, adx, adx_neg, adx_pos
from ta.momentum import stoch, stoch_signal
from ta.volatility import bollinger_hband, bollinger_lband, bollinger_mavg

# Upstox API
from upstox_api.api import *

# Python Django Core Libraries
import hashlib
from django.core.cache import caches, cache
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError, PermissionDenied, ImproperlyConfigured, MultipleObjectsReturned
from django.http import (HttpResponseRedirect, HttpResponseForbidden, HttpResponse, JsonResponse)
from django.shortcuts import redirect, render, get_object_or_404, resolve_url
import requests, functools, importlib, sys
from django.db import transaction

# Exception Errors
from requests.exceptions import HTTPError
from json.decoder import JSONDecodeError

# Django Signals
from django.db.models.signals import post_save, post_delete, m2m_changed, pre_save, pre_delete
from django.dispatch import receiver, Signal

# Rest Frame Work
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
# Defaul Djnago Models
from django.contrib.auth.models import User, Group, Permission
from django.db.models import Max, Min, Sum, Q
from django.db.models.query import QuerySet

# Default Djnago Views
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, View, TemplateView, FormView

# Django Filters
import django_filters

# DJnago Celery
from heystox_trade.celery import app as celery_app
from celery.schedules import crontab
from celery import group
from celery.exceptions import WorkerLostError

# Import Redis
import redis

# Import Multiselect Field
from multiselectfield import MultiSelectField

# Custom Exceptions
from .custom_exception import *

# Import Export Library
from import_export import resources
from import_export.admin import ExportMixin

# ATTRIBUTE & FUNCTIONS FOR IMPORTS

default_timezone = pytz.timezone(settings.TIME_ZONE)

def get_local_time():
    return default_timezone.localize(datetime.now())

redis_cache = caches["redis"]


# Upstox Dictionary

order_schema = {
    "transaction_type" : None,
    "symbol" : None,
    "order_type": None,
    "quantity": None,
    "price": None,
    "duarion_type": None,
}

transaction_types = {
    "BUY" : TransactionType.Buy,
    "SELL" : TransactionType.Sell
}

order_types = {
    "MARKET" : OrderType.Market,
    "LIMIT" : OrderType.Limit,
    "SL" : OrderType.StopLossLimit,
    "SLM" : OrderType.StopLossMarket
}

product_types = {
    "INTRADAY": ProductType.Intraday,
    "DELIVERY": ProductType.Delivery
}

duration_types = {
    "DAY" : DurationType.DAY,
    "IOC" : DurationType.IOC #Immidiate or Cancel Order
}

stock_movement = {
    "BUY" : settings.MARKET_BULLISH_MOVEMENT,
    "SELL" : settings.MARKET_BEARISH_MOVEMENT
}

# Candle Choices
candles_types = {
        "M5": "5 Minute",
        "M10": "10 Minute",
        "M15": "15 Minute",
        "M30": "30 Minute",
        "M60": "60 Minute",
        "1H": "1 Hour", 
        "1D": "1 Day"
}

strategies_for = {
    "EI" : "EquityIntraday",
    "EF" : "EquityFutures"
}

def roundup(x, prec=2, base=.05):
  return round(base * round(float(x)/base), prec)



def is_time_between_range(obj_time, last_minutes):
    after_time = get_local_time().now() - timedelta(minutes=last_minutes)
    if obj_time >= after_time:
        return True
    return False


def get_stock_stoploss_price(price, entry_type, stoploss_percent:float=None):
    if stoploss_percent is None:
        stoploss_percent = settings.DEFAULT_STOPLOSS
    if price < 100:
        sl = 0.10
    elif price < 200:
        sl =  0.20
    elif price < 300:
        sl = 0.40
    else:
        sl = 0.70
    sl += stoploss_percent
    stoploss = price * sl /100
    return roundup(price + stoploss if entry_type == "SELL" else price - stoploss)


def get_stock_target_price(price, entry_type, target_percent:float=None):
    if target_percent is None:
        target_percent = settings.DEFAULT_TARGET
    if price < 100:
        tg = 0.5
    elif price < 200:
        tg = 0.40
    elif price < 300:
        tg = 0.80
    else:
        tg = abs(price - get_stock_stoploss_price(price, entry_type)) * 2
        return roundup(price - tg if entry_type == "SELL" else price + tg)
    tg += target_percent
    tgt = price * tg/ 100
    return roundup(price - tgt if entry_type == "SELL" else price + tgt)


def get_stoploss_saver_price(price, entry_type):
    hit_price = get_stock_stoploss_price(price, "BUY" if entry_type == "SELL" else "SELL")
    if price < 100:
        pp = 0.5
    elif price < 200:
        pp = 0.40
    elif price < 300:
        pp = 0.80
    else:
        pp = 0.80
    return roundup(hit_price + pp if entry_type == "BUY" else hit_price - pp)


def get_auto_exit_price(price, entry_type):
    fixed_auto_exit_percentage = settings.DEFAULT_STOPLOSS / 2
    if price < 100:
        sl = fixed_auto_exit_percentage
    elif price < 200:
        sl = fixed_auto_exit_percentage + 0.10
    elif price < 300:
        sl = fixed_auto_exit_percentage + 0.15
    else:
        sl = fixed_auto_exit_percentage + 0.20
    if entry_type == "SELL":
        stoploss = price - (price * sl /100)
        return roundup(stoploss)
    elif entry_type == "BUY":
        stoploss = price + (price * sl /100)
        return roundup(stoploss)


def generate_random_string(length:str):
    letters = string.ascii_letters
    random_string = "".join(random.choice(letters) for i in range(length+1))
    return random_string

# Django Models Choices
# Strategy Model
