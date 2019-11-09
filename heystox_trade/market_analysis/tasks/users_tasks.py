from django.core.cache import cache
from celery.task import periodic_task
from celery.schedules import crontab
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

@periodic_task(run_every=(crontab(day_of_month=1, hour=7, minute=30)), name="update_all_users_starting_fund")
def update_initial_balance():
    """This function will run on 1st of every month and update balance of user"""
    users = User.objects.filter(for_trade=True).prefetch_related("bank")
    for user in users:
        upstox_user = get_upstox_user(user)
        balance = upstox_user.get_balance()
        current_balance = balance.get("equity").get("available_margin")
        user.bank.initial_balance = current_balance
        user.bank.save()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=2, minute=2)), name="update_daily_earning_of_user")
def update_current_earning_balance():
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
            user.bank.current_balance = current_balance
            user.bank.save(update_fields=["current_balance"])

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=2, minute=5)), name="stop_trading_on_profit_loss")    
def stop_trading_on_profit_loss():
    """This Function will run in every morning to check if user is in loss or in profit then stop trading accordingly"""
    users = User.objects.filter(for_trade=False).prefetch_related("bank")
    for user in users:
        current_balance = user.bank.current_balance
        initial_balance = user.bank.initial_balance
        bearable_loss = initial_balance * 80 /100
        expected_profit = (initial_balance * 35 /100) + initial_balance
        if current_balance < bearable_loss:
            user.user_profile.for_trade = False
        elif current_balance > expected_profit:
            user.user_profile.for_trade = False
        user.user_profile.save() 




