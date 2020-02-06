from django.contrib.auth.models import User
from django.db.models.signals import post_save
from market_analysis.models import UserProfile, BankDetail, Earning, SortedStocksList, StrategyTimestamp
from django.dispatch import receiver
from datetime import datetime
from market_analysis.tasks.day_trading_tasks import order_on_macd_verification, find_pdhl_stocks, take_entry_for_long_short
from rest_framework.authtoken.models import Token
# Code Below

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    if created:
        user_profile = UserProfile.objects.get_or_create(user=instance)
        Token.objects.get_or_create(user=instance)

@receiver(post_save, sender=BankDetail)
def create_earning_object(sender, instance, update_fields, **kwargs):
    if update_fields and "current_balance" in update_fields:
        Earning.objects.get_or_create(user=instance.user_profile, date=datetime.now().date(), opening_balance=instance.current_balance)

@receiver(post_save, sender=StrategyTimestamp)
def verify_macd_signal(instance, **kwargs):
    if instance.indicator.name == "MACD" and instance.is_last_timestamp():
        stock = instance.stock
        try:
            stochastic_timestamp = stock.get_second_last_timestamp()
        except:
            stochastic_timestamp = None
        if stochastic_timestamp and stochastic_timestamp.indicator.name == "STOCHASTIC":
            order_on_macd_verification.delay(instance.id, stochastic_timestamp.id)

@receiver(post_save, sender=SortedStocksList)
def verify_stock_pdhl_longshort(sender, instance, **kwargs):
    if instance:
        find_pdhl_stocks.delay(instance.id)
        take_entry_for_long_short.delay(instance.id)

