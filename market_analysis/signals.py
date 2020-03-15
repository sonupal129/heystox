from market_analysis.imports import *
from market_analysis.models import UserProfile, BankDetail, Earning, SortedStocksList, StrategyTimestamp

from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.indicator_signals import macd_stochastic_signal
from market_analysis.tasks.intraday_indicator import is_stock_pdhl, has_entry_for_long_short
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
def verify_macd_signal(sender, instance, created, **kwargs):
    if created:
        if instance.indicator.name == "MACD" and instance.is_last_timestamp():
            stock = instance.stock
            try:
                secondlast_timestamp = stock.get_second_last_timestamp()
            except:
                secondlast_timestamp = None
            if secondlast_timestamp and secondlast_timestamp.indicator.name == "STOCHASTIC":
                macd_stochastic_signal.delay(instance.id, secondlast_timestamp.id)

@receiver(post_save, sender=SortedStocksList)
def verify_stock_pdhl_longshort(sender, instance, **kwargs):
    if kwargs.get("created"):
        is_stock_pdhl.delay(instance.id)
        has_entry_for_long_short.delay(instance.id)

