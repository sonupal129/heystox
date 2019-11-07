from django.core.cache import cache
from celery import Celery
from celery.decorators import task, periodic_task
from celery.task.schedules import crontab
from upstox_api.api import *
from django.contrib.auth.models import User
from market_analysis.models import Earning
from datetime import timedelta, datetime
import time
# START CODE BELOW

def get_upstox_user(user):
    """Returns upstox logged in user object"""
    user = cache.get(user.email + "_upstox_login_user")
    return user

def update_initial_balance(user_id=1):
    """This function will run on 1st of every month and update balance of user"""
    users = User.objects.filter(for_trade=True).prefetch_related("bank")
    for user in users:
        upstox_user = get_upstox_user(user)
        balance = upstox_user.get_balance()
        current_balance = balance.get("equity").get("available_margin")
        user.bank.initial_balance = current_balance
        user.bank.save()

def update_current_earning_balance(user_id=1):
    """This function will update daily earnings and current balance of user"""
    users = User.objects.filter(for_trade=True).prefetch_related("bank")
    for user in users:
        upstox_user = get_upstox_user(user)
        balance = upstox_user.get_balance()
        current_balance = balance.get("equity").get("available_margin")
        if user.bank.current_balance != current_balance:
            pl = Earning.objects.get(user=user.user_profile, date=datetime.now().date() - timedelta(1))
            pl.profit_loss = current_balance - pl.opening_balance
            pl.save()
            user.bank.current_balance = current_balance:
            user.bank.save(update_fields=["current_balance"])
    
def stop_trading_on_profit_loss(user_id=1):
    """This Function will run in every morning to check if user is in loss or in profit then stop trading accordingly"""
    user = User.objects.get(id=user_id)
    current_balance = user.bank.current_balance
    initial_balance = user.bank.initial_balance
    bearable_loss = initial_balance * 80 /100
    expected_profit = (initial_balance * 35 /100) + initial_balance
    if current_balance < bearable_loss:
        user.user_profile.for_trade = False
    elif current_balance > expected_profit:
        user.user_profile.for_trade = False
    user.user_profile.save() 




