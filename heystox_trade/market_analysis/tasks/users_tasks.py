from django.core.cache import cache
from django.contrib.auth.models import User
from market_analysis.models import Earning, UserProfile
from datetime import timedelta, datetime
from market_analysis.tasks.notification_tasks import slack_message_sender
from celery import shared_task

# START CODE BELOW

@shared_task
def update_initial_balance():
    """This function will run on 1st of every month and update balance of user"""
    user_profiles = UserProfile.objects.filter(for_trade=True).prefetch_related("bank")
    for user_profile in user_profiles:
        user_profile.update_initial_balance()

@shared_task
def update_current_earning_balance():
    """This function will update daily earnings and current balance of user"""
    user_profiles = UserProfile.objects.filter(for_trade=True).prefetch_related("bank")
    for user_profile in user_profiles:
        user_profile.update_current_earning_balance()

@shared_task
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
    return "Trading Data Updated"

@shared_task
def authenticate_users_in_morning():
    user_profiles = UserProfile.objects.filter(for_trade=True)
    for user_profile in user_profiles:
        message = "Login URL for " + user_profile.user.get_full_name() + ": " + user_profile.get_authentication_url()
        slack_message_sender.delay(text=message)

