from market_analysis.imports import *
from market_analysis.models import (UserProfile, BankDetail, Earning, SortedStocksList, StrategyTimestamp, Order, Strategy, Symbol)
from market_analysis.tasks.strategies.backtest import delete_backtesting_data, create_backtesting_data
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.indicator_signals import SignalRouter
# from market_analysis.tasks.intraday_indicator import is_stock_pdhl, has_entry_for_long_short
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
def send_strategy_signal_to_router(sender, instance, **kwargs):
    if kwargs.get("created"):
        if instance.strategy.strategy.priority_type in ["PR", "SC"]:
            transaction.on_commit(lambda : SignalRouter(instance).route_signal())

# @receiver(post_save, sender=SortedStocksList)
# def verify_stock_pdhl_longshort(sender, instance, **kwargs):
#     if kwargs.get("created"):
#         is_stock_pdhl.delay(instance.id)
#         has_entry_for_long_short.delay(instance.id)


@receiver(post_save, sender=Order)
def send_slack_on_order_rejection(sender, instance, **kwargs):
    """Send slack message if any error in order like order rejeceted or cancelled by broker"""
    if instance.status in ["CA", "RE"]:
        slack_message_sender.delay(f"Order {instance.order_id}, {instance.get_status_display()}, Please Check!")

    
@receiver(m2m_changed, sender=Symbol.strategy.through)
def invalidate_strategies_cache(sender, instance, action, **kwargs):
    entry_cache_key = "_".join([instance.symbol, "Entry", "strategies"])
    exit_cache_key = "_".join([instance.symbol, "Exit", "strategies"])
    redis_cache.delete(entry_cache_key)
    redis_cache.delete(exit_cache_key)

@receiver(pre_save, sender=Strategy)
def call_delete_backtesting_data(sender, instance, **kwargs):
    """Signal will call celery task which will delete all backtested report data when backtesting_ready
    will be false from true also this function invalidate all cache key of that strategy"""
    try:
        new_value = instance.backtesting_ready
        old_value = Strategy.objects.get(id=instance.id).backtesting_ready
        if new_value == False and old_value == True:
            # Call delete task which will delete all backtest reports
            delete_backtesting_data.delay(instance.strategy_name)
            for key in redis_cache.keys("*"):
                if instance.strategy_name in key:
                    redis_cache.delete(key)
    except:
        pass

@receiver(pre_save, sender=Strategy)
def call_create_backtesting_data(sender, instance, **kwargs):
    """Signal will call celery task which will create all backtested report data for all stock(liquid stock) when backtesting_ready
    will be true from false"""
    try:
        new_value = instance.backtesting_ready
        old_value = Strategy.objects.get(id=instance.id).backtesting_ready
        if new_value == True and old_value == False:
            # Call task which will create backtest report for all stocks all backtest reports
            create_backtesting_data.delay(instance.id)
    except:
        pass


