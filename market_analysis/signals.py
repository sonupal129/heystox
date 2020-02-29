from market_analysis.imports import *
from market_analysis.models import UserProfile, BankDetail, Earning, SortedStocksList, StrategyTimestamp
from market_analysis.tasks.day_trading_tasks import order_on_macd_verification, take_entry_for_long_short, is_stock_pdhl
from market_analysis.tasks.notification_tasks import slack_message_sender
# Code Below

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    user_profile = UserProfile.objects.get_or_create(user=instance)
    Token.objects.get_or_create(user=instance)

@receiver(post_save, sender=BankDetail)
def create_earning_object(sender, instance, update_fields, **kwargs):
    if update_fields and "current_balance" in update_fields:
        Earning.objects.get_or_create(user=instance.user_profile, date=get_local_time().date(), opening_balance=instance.current_balance)

@receiver(post_save, sender=StrategyTimestamp)
def verify_macd_signal(instance, **kwargs):
    if instance.indicator.name == "MACD" and instance.is_last_timestamp():
        stock = instance.stock
        try:
            secondlast_timestamp = stock.get_second_last_timestamp()
        except:
            secondlast_timestamp = None
        if secondlast_timestamp and secondlast_timestamp.indicator.name == "STOCHASTIC":
            slack_message_sender.delay(text=f"STOCHASTIC and MACD Found for Stock {instance.stock}", channel="#random")
            order_on_macd_verification.delay(instance.id, secondlast_timestamp.id)

@receiver(post_save, sender=SortedStocksList)
def verify_stock_pdhl_longshort(sender, instance, **kwargs):
    # is_stock_pdhl.delay(instance.id)
    # take_entry_for_long_short.delay(instance.id)
    pass

