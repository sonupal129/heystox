from django.core.cache import cache
from celery.task import periodic_task
from celery.schedules import crontab

from django.contrib.auth.models import User
from market_analysis.models import Earning, UserProfile
from datetime import timedelta, datetime
import time
from market_analysis.tasks.tasks import slack_message_sender
# START CODE BELOW

@periodic_task(run_every=(crontab(day_of_month=1, hour=1, minute=32)),queue="default", options={"queue": "default"}, name="update_all_users_starting_fund")
def update_initial_balance():
    """This function will run on 1st of every month and update balance of user"""
    user_profiles = UserProfile.objects.filter(for_trade=True).prefetch_related("bank")
    for user_profile in user_profiles:
        user_profile.update_initial_balance()

@periodic_task(run_every=(crontab(day_of_week="2-6", hour=8, minute=55)),queue="default", options={"queue": "default"}, name="update_daily_earning_of_user")
def update_current_earning_balance():
    """This function will update daily earnings and current balance of user"""
    user_profiles = UserProfile.objects.filter(for_trade=True).prefetch_related("bank")
    for user_profile in user_profiles:
        user_profile.update_current_earning_balance()

@periodic_task(run_every=(crontab(day_of_week="2-6", hour=2, minute=5)),queue="default", options={"queue": "default"}, name="stop_trading_on_profit_loss")    
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

@periodic_task(run_every=(crontab(day_of_week="1-5", hour=7, minute=30)),queue="default", options={"queue": "default"}, name="create_new_authentication_daily")
def authenticate_users_in_morning():
    user_profiles = UserProfile.objects.filter(for_trade=True)
    for user_profile in user_profiles:
        message = "Login URL for " + user_profile.user.get_full_name() + ": " + user_profile.get_authentication_url()
        slack_message_sender.delay(text=message)

