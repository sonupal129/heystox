from market_analysis.imports import *
from .base_strategy import BaseEntryStrategy
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.signals import *
from market_analysis.models import Symbol, SortedStocksList, DeployedStrategies, StrategyTimestamp
from market_analysis.tasks.trading import get_upstox_user
# CODE BELOW

class RangeReversalStrategy(BaseEntryStrategy):
    """DOC"""
    name = "higher_range_reversal_strategy"
    queue = "torrent_shower"

    def higher_range_reversal_strategy(self, stock_id, entry_type, *args, **kwargs):
        
        data = kwargs["data"]
        # print(kwargs)
        # print(args)
        symbol_name = data["symbol"].lower()
        today_date = get_local_time()
        cache_key = "_".join([symbol_name, "range_reversal_strategy", "cached_high_low_data", str(today_date.date())])
        cached_value = redis_cache.get(cache_key)
        
        if cached_value:
            if not cached_value.get("entry_found"):
                high_trigger_price = cached_value["high_trigger_price"]
                low_trigger_price = cached_value["low_trigger_price"]
                # high_price =  cached_value["high_price"]
                # low_price =  cached_value["low_price"]
                ticker_high_price = data["high"]
                ticker_low_price = data["low"]
                ticker_ltp_price = data["ltp"]
                trigger_time = cached_value.get("trigger_time", None)
                if not trigger_time:
                    if ticker_high_price >= high_trigger_price:
                        cached_value["trigger_time"] = today_date.now()
                        cached_value["trigger_side"] = "HIGH"
                        cached_value["trigger_price"]  = ticker_high_price
                        redis_cache.set(cache_key, cached_value, 9*60*60)
                    elif ticker_low_price <= low_trigger_price:
                        cached_value["trigger_time"] = today_date.now()
                        cached_value["trigger_side"] = "LOW"
                        cached_value["trigger_price"] = ticker_low_price
                        redis_cache.set(cache_key, cached_value, 9*60*60)
                else:
                    after_trigger_time = trigger_time + timedelta(minutes=13)
                    trigger_side = cached_value["trigger_side"]
                    if today_date.now() >= after_trigger_time:     
                        entry_found = False
                        if trigger_side == "HIGH":
                            levelup_high_price =  cached_value["levelup_high_price"]
                            leveldown_high_price =  cached_value["leveldown_high_price"]
                            if ticker_ltp_price > levelup_high_price:
                                entry_found = True
                                entry_type = "BUY"
                            elif ticker_ltp_price < leveldown_high_price:
                                entry_found = True
                                entry_type = "SELL"
                        elif trigger_side == "LOW":
                            levelup_low_price =  cached_value["levelup_low_price"]
                            leveldown_low_price =  cached_value["leveldown_low_price"]
                            if ticker_ltp_price > levelup_low_price:
                                entry_found = True
                                entry_type = "BUY"
                            elif ticker_ltp_price < leveldown_low_price:
                                entry_found = True
                                entry_type = "SELL"
                        if entry_found:
                            cached_value["entry_found"] = True
                            cached_value["entry_time"] = today_date.now()
                            redis_cache.set(cache_key, cached_value, 9*60*60)
                            return self.make_response(stock_id, entry_type, ticker_ltp_price, today_date.now())
        return "No Entry"

    def make_response(self, stock_id, entry_type, ltp, entry_time, **kwargs):
        if not entry_type in ["BUY", "SELL"]:
            raise AttributeError("entry_type should be BUY or Sell")
        data = {
            "stock_id": stock_id,
            "entry_type": entry_type,
            "entry_price": float(ltp),
            "entry_time": entry_time,
            **kwargs
            }
        return data

    def create_indicator_timestamp(self, stock_id, entry_type, entry_price:float, entry_time:object, **kwargs):
        if kwargs.get("backtest"):
            raise TypeError("Backtesting is not allowed")
        current_time = get_local_time()
        entry_time = entry_time.replace(microsecond=0)
        symbol = Symbol.objects.get(id=stock_id)
        sorted_stock, is_created = SortedStocksList.objects.update_or_create(symbol=symbol, created_at__date=current_time.date(), entry_type=entry_type, defaults={"added" : "ML" })
        deployed_strategy = symbol.deployed_strategies.get(strategy__strategy_name=self.__class__.__name__, entry_type=entry_type, timeframe=None, active=True)
        stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, strategy=deployed_strategy, timestamp__range=[entry_time - timedelta(minutes=20), entry_time + timedelta(minutes=20)]).order_by("timestamp")
        if not stamp.exists():
            if entry_time.date() == current_time.date():
                stamp = StrategyTimestamp.objects.create(stock=sorted_stock, strategy=deployed_strategy, timestamp=entry_time)
                stamp.entry_price = entry_price
                stamp.save()
        elif stamp.count() > 1:
            stamp.exclude(id=stamp.first().id).delete()
        message = f"Entry Found RANGEREVERSAL for {symbol.symbol} {entry_type}, {entry_price} {entry_time}"
        slack_message_sender.delay(text=message, channel="#random")
        return True



celery_app.tasks.register(RangeReversalStrategy)

@celery_app.task(queue="low_priority", ignore_result=True)
def prepare_data_for_range_reversal_strategy():
    days = 5 

    def trigger_price(price, price_type, percentage=0.10):
        trigger_amount = price * percentage / 100
        if price_type == "HIGH":
            price = price + trigger_amount
        elif price_type == "LOW":
            price = price - trigger_amount
        return roundup(price)

    symbols  = Symbol.objects.filter(Q(trade_realtime__contains="BUY") | Q(trade_realtime__contains="SELL")).distinct()
    today_date = get_local_time().date()
    previous_date = today_date - timedelta(days=1)
    for symbol in symbols:
        cache_key = "_".join([symbol.symbol, "range_reversal_strategy", "cached_high_low_data", str(today_date)])
        high_price = symbol.get_stock_high_low_price(previous_date, "HIGH", days=days-1) # This will inclue +1 days so 5 days will give 6 days data so removing 1 day to get last 5 days data
        low_price = symbol.get_stock_high_low_price(previous_date, "LOW", side="lowest", days=days-1) # This will inclue +1 days so 5 days will give 6 days data so removing 1 day to get last 5 days data
        data = {
            "high_price": high_price,
            "high_trigger_price": trigger_price(high_price, "LOW"),
            "levelup_high_price": trigger_price(high_price, "HIGH", 0.20),
            "leveldown_high_price": trigger_price(high_price, "LOW", 0.20),
            "low_price": low_price,
            "low_trigger_price": trigger_price(low_price, "HIGH"),
            "levelup_low_price": trigger_price(low_price, "HIGH", 0.20),
            "leveldown_low_price": trigger_price(low_price, "LOW", 0.20)
        }
        redis_cache.set(cache_key, data, 9*60*60)
    return True



def func(message):
    print(message)

def func2(message):
    print(message)