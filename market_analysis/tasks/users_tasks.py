from market_analysis.models import Earning, UserProfile
from .notification_tasks import slack_message_sender
from market_analysis.imports import *

# START CODE BELOW

@celery_app.task(queue="low_priority")
def update_initial_balance():
    """This function will run on 1st of every month and update balance of user"""
    for user_profile in UserProfile.objects.filter(for_trade=True).prefetch_related("bank"):
        user_profile.update_initial_balance()

@celery_app.task(queue="low_priority")
def update_current_earning_balance():
    """This function will update daily earnings and current balance of user"""
    for user_profile in UserProfile.objects.filter(for_trade=True).prefetch_related("bank"):
        user_profile.update_current_earning_balance()

@celery_app.task(queue="low_priority")
def stop_trading_on_profit_loss():
    """This Function will run in every morning to check if user is in loss or in profit then stop trading accordingly"""
    for user_profile in UserProfile.objects.filter(for_trade=True).select_related("bank"):
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

@celery_app.task(queue="low_priority")
def authenticate_users_in_morning():
    for user_profile in UserProfile.objects.filter(for_trade=True):
        message = "Login URL for " + user_profile.user.get_full_name() + ": " + user_profile.get_authentication_url()
        slack_message_sender.delay(text=message)

@celery_app.task(queue="low_priority", autoretry_for=(HTTPError,), retry_kwargs={'max_retries': 2, 'countdown': 10}, max_retries=10)
def login_upstox_user(email):
    user_profile = UserProfile.objects.get(user__email=email)
    try:
        upstox_user = Upstox(user_profile.credential.api_key, user_profile.credential.access_token)
        cache.set(email + "_upstox_login_user", upstox_user, 30*60*48)
    except HTTPError as e:
        slack_message_sender.delay(text="Unable to log in upstox trying again: " + str(e))
        raise HTTPError("Unable to authenticate")
    return "Successfully Loged-In in Upstox"
