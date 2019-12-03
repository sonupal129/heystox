from django.core.cache import cache
from celery.task import periodic_task
from celery.schedules import crontab
from upstox_api.api import *
from django.contrib.auth.models import User
from market_analysis.models import Earning, UserProfile
from datetime import timedelta, datetime
from heystox_trade.settings import upstox_redirect_url
import time
from market_analysis.tasks.tasks import slack_message_sender
from heystox_intraday.intraday_fetchdata import get_upstox_user
# START CODE BELOW

@periodic_task(run_every=(crontab(day_of_month=1, hour=7, minute=30)), name="update_all_users_starting_fund")
def update_initial_balance():
    """This function will run on 1st of every month and update balance of user"""
    user_profiles = UserProfile.objects.filter(for_trade=True).prefetch_related("bank")
    for user_profile in user_profiles:
        upstox_user = get_upstox_user(user_profile.user.email)
        balance = upstox_user.get_balance()
        current_balance = balance.get("equity").get("available_margin")
        user_profile.bank.initial_balance = current_balance
        user_profile.bank.save()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=2, minute=2)), name="update_daily_earning_of_user")
def update_current_earning_balance():
    """This function will update daily earnings and current balance of user"""
    user_profiles = UserProfile.objects.filter(for_trade=True).prefetch_related("bank")
    for user_profile in user_profiles:
        upstox_user = get_upstox_user(user_profile.user.email)
        balance = upstox_user.get_balance()
        current_balance = balance.get("equity").get("available_margin")
        if user_profile.bank.current_balance != current_balance:
            pl = None
            try:
                pl = Earning.objects.get(user=user_profile, date=datetime.now().date() - timedelta(1))
            except:
                pl = Earning.objects.create(user=user_profile, date=datetime.now().date() - timedelta(1), opening_balance=user_profile.bank.current_balance)
            pl.profit_loss = float(current_balance) - float(pl.opening_balance)
            pl.save()
            user_profile.bank.current_balance = current_balance
            user_profile.bank.save(update_fields=["current_balance"])

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=2, minute=5)), name="stop_trading_on_profit_loss")    
def stop_trading_on_profit_loss():
    """This Function will run in every morning to check if user is in loss or in profit then stop trading accordingly"""
    user_profiles = UserProfile.objects.filter(for_trade=True).prefetch_related("bank")
    for user_profile in user_profiles:
        current_balance = user_profile.bank.current_balance
        initial_balance = user_profile.bank.initial_balance
        bearable_loss = initial_balance * 80 /100
        expected_profit = (initial_balance * 35 /100) + initial_balance
        if current_balance < bearable_loss:
            user_profile.for_trade = False
        elif current_balance > expected_profit:
            user_profile.for_trade = False
        user_profile.save()

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=8, minute=0)), name="create_new_authentication_daily")
def authenticate_users_in_morning():
    user_profiles = UserProfile.objects.filter(for_trade=True)
    for user_profile in user_profiles:
        session = Session(user_profile.credential.api_key)
        session.set_redirect_uri(upstox_redirect_url)
        session.set_api_secret(user_profile.credential.secret_key)
        cache_key = user_profile.user.email + "_upstox_user_session"
        cache.set(cache_key, session)
        login_url = session.get_login_url()
        message = "Login URL for " + user_profile.user.get_full_name() + ": " + login_url
        slack_message_sender.delay(text=message)

