from market_analysis.imports import *
from market_analysis.models import (UserProfile, BankDetail, Earning, SortedStocksList, StrategyTimestamp, Order, Strategy, Symbol, BacktestReport, DeployedStrategies, SortedStockDashboardReport)
from market_analysis.tasks.strategies.backtest import delete_backtesting_data
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.indicator_signals import SignalRouter
from market_analysis.signals import *
from market_analysis.tasks.strategies.realtime_trade_strategy import RangeReversalStrategy
# from market_analysis.tasks.intraday_indicator import is_stock_pdhl, has_entry_for_long_short
# Code Below

@receiver(post_save, sender=User)
def create_token_and_user_profile(sender, instance, created, **kwargs):
    user_profile = UserProfile.objects.get_or_create(user=instance)
    Token.objects.get_or_create(user=instance)

@receiver(post_save, sender=BankDetail)
def create_earning_object(sender, instance, update_fields, **kwargs):
    if update_fields and "current_balance" in update_fields:
        Earning.objects.get_or_create(user=instance.user_profile, date=get_local_time().date(), opening_balance=instance.current_balance)


@receiver(post_save, sender=StrategyTimestamp)
def send_strategy_signal_to_router(sender, instance, **kwargs):
    today_date = get_local_time().date()
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
        slack_message_sender.delay(text=f"Order {instance.order_id}, {instance.get_status_display()}, Please Check!") 

@receiver(pre_delete, sender=Strategy)
def delete_backtesting_data_on_strategy_delete(sender, instance, **kwargs):
    """Signal will delete all backtested report data that strategy when strategy get deleted"""
    BacktestReport.objects.filter(strategy_name=instance.strategy_name).delete()

@receiver(pre_delete, sender=Strategy)
def delete_deployed_strategies(sender, instance, **kwargs):
    """Delete deployed strategies on delete strategies"""
    DeployedStrategies.objects.filter(strategy__strategy_name=instance.strategy_name).delete()

@receiver(pre_save, sender=Strategy)
def delete_backtesting_data_by_timeframe(sender, instance, **kwargs):
    """Signal will call celery task which will delete backtested report data when backtesting_ready
    will be false also this function invalidate all cache key of that strategy, it deletes by timeframe"""
    if not instance.backtesting_ready:
        try:
            new_value = instance.timeframe
            old_value = Strategy.objects.get(id=instance.id).timeframe

            for value in old_value:
                if value not in new_value:
                    delete_backtesting_data.delay(strategy_name=instance.strategy_name, timeframe=value)
            return True
        except:
            pass

@receiver(post_save, sender=Order)
def update_orders_quantity(sender, instance, **kwargs):
    today_date = get_local_time().date()
    cache_key = str(today_date) + "_total_order_quantity"
    orders = Order.objects.filter(entry_time__date=today_date, status="CO", entry_type="ET").count()
    redis_cache.set(cache_key, orders, 12*60*60)


# Strategy Caller

@receiver(call_strategy)
def call_realtime_entry_strategies(sender, **kwargs):
    symbol = kwargs["symbol"] 
    stock_id = kwargs["symbol_id"]
    data = kwargs["data"]
    realtime_strategies = symbol.get_realtime_strategies()
    for strategy in realtime_strategies:
        strategy.call_entry_strategy(stock_id=stock_id, data=data)

@receiver(update_profit_loss)
def update_sorted_stocks_dashboard_pl(sender, **kwargs):
    today_date = get_local_time().date()
    try:
        dashboard = SortedStockDashboardReport.objects.get(name=kwargs["symbol"], created_at__date=today_date, entry_type=kwargs["entry_type"], target_price=kwargs["target_price"], stoploss_price=kwargs["stoploss_price"])
        dashboard.exit_price = kwargs["exit_price"]
        dashboard.exit_time = get_local_time().now()
        if dashboard.entry_type == 'BUY':
            dashboard.pl = dashboard.exit_price - dashboard.entry_price
        elif dashboard.entry_type == "SELL":
            dashboard.pl = roundup(dashboard.entry_price - dashboard.exit_price)
        dashboard.save()
    except:
        pass
