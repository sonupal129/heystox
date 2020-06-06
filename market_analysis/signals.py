from market_analysis.imports import *
from market_analysis.models import (UserProfile, BankDetail, Earning, SortedStocksList, StrategyTimestamp, Order, Indicator, Strategy, Symbol)

from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.indicator_signals import prepare_orderdata_from_signal
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
def send_signal_on_indicator_object_creation(sender, instance, created, **kwargs):
    if created:
        if instance.indicator.name in Indicator.objects.filter(indicator_type="PR").values_list("name", flat=True):
            prepare_orderdata_from_signal.delay(instance.id)


@receiver(post_save, sender=SortedStocksList)
def verify_stock_pdhl_longshort(sender, instance, **kwargs):
    if kwargs.get("created"):
        is_stock_pdhl.delay(instance.id)
        has_entry_for_long_short.delay(instance.id)


@receiver(post_save, sender=Order)
def send_slack_on_order_rejection(sender, instance, **kwargs):
    """Send slack message if any error in order like order rejeceted or cancelled by broker"""
    if instance.status in ["CA", "RE"]:
        slack_message_sender.delay(f"Order {instance.order_id}, {instance.get_status_display()}, Please Check!")

    
@receiver(m2m_changed, sender=Symbol.entry_strategy.through)
@receiver(m2m_changed, sender=Symbol.exit_strategy.through)
def invalidate_strategies_cache(sender, instance, action, **kwargs):
    entry_cache_key = "_".join([instance.symbol, "Entry", "strategies"])
    exit_cache_key = "_".join([instance.symbol, "Exit", "strategies"])
    print("Signal Called")
    redis_cache.delete(entry_cache_key)
    redis_cache.delete(exit_cache_key)



