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
import csv

# TA LIbrary for Stock Market
from ta.trend import macd, macd_diff, macd_signal, ema, ema_indicator
from ta.momentum import stoch, stoch_signal
from ta.volatility import bollinger_hband, bollinger_lband, bollinger_mavg

# Upstox API
from upstox_api.api import *

# Python Django Core Libraries
import hashlib
from django.core.cache import caches, cache
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError, PermissionDenied, ImproperlyConfigured
from requests.exceptions import HTTPError
from django.http import (HttpResponseRedirect, HttpResponseForbidden, HttpResponse, JsonResponse)
from django.shortcuts import redirect, render, get_object_or_404, resolve_url
import requests

# Django Signals
from django.db.models.signals import post_save
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
from django.db.models import Max, Min, Sum

# Defaul Djnago Views
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, View, TemplateView

# Django Filters
import django_filters

# DJnago Celery
from heystox_trade.celery import app as celery_app
from celery.schedules import crontab

# Import Redis
import redis

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



def roundup(x, prec=2, base=.05):
  return round(base * round(float(x)/base), prec)