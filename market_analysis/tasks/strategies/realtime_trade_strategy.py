from market_analysis.imports import *
from .base_strategy import BaseEntryStrategy
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.signals import *
from market_analysis.models import Symbol
from market_analysis.tasks.trading import get_upstox_user
# CODE BELOW

class RangeReversalStrategy(BaseEntryStrategy):
    """DOC"""
    name = "higher_range_reversal_strategy"
    queue = "tickers"

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
                high_price =  cached_value["high_price"]
                low_price =  cached_value["low_price"]
                ticker_high_price = data["high"]
                ticker_low_price = data["low"]
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
                        ticker_ltp_price = data["ltp"]
                        entry_found = False
                        if trigger_side == "HIGH":
                            if ticker_ltp_price > high_trigger_price:
                                entry_found = True
                                entry_type = "BUY"
                            elif ticker_ltp_price < high_trigger_price:
                                entry_found = True
                                entry_type = "SELL"
                        elif trigger_side == "LOW":
                            if ticker_ltp_price > low_trigger_price:
                                entry_found = True
                                entry_type = "BUY"
                            elif ticker_ltp_price < low_trigger_price:
                                entry_found = True
                                entry_type = "SELL"
                        if entry_found:
                            cached_value["entry_found"] = True
                            cached_value["entry_time"] = today_date.now()
                            redis_cache.set(cache_key, cached_value, 9*60*60)
                            return self.make_response(stock_id, entry_type, ticker_ltp_price, today_date.now())
        return "No Entry"

    def make_response(self, stock_id, entry_type, ltp, entry_time, **kwargs):
        if not (entry_type == "BUY" or entry_type == "SELL"):
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
        symbol = Symbol.objects.get(id=stock_id)
        message = f"Entry Found RANGEREVERSAL for {symbol.symbol} {entry_type}, {entry_price} {entry_time}"
        slack_message_sender.delay(text=message, channel="#random")
        return True



celery_app.tasks.register(RangeReversalStrategy)

@celery_app.task(queue="low_priority", ignore_result=True)
def prepare_data_for_range_reversal_strategy():
    days = 5

    def trigger_price(price, price_type):
        trigger_amount = price * 0.10 / 100
        if price_type == "HIGH":
            price = price - trigger_amount
        elif price_type == "LOW":
            price = price + trigger_amount
        return roundup(price)

    symbols  = Symbol.objects.filter(Q(trade_realtime__contains="BUY") | Q(trade_realtime__contains="SELL")).distinct()
    today_date = get_local_time().date()
    previous_date = today_date - timedelta(days=1)
    for symbol in symbols:
        cache_key = "_".join([symbol.symbol, "range_reversal_strategy", "cached_high_low_data", str(today_date)])
        high_price = symbol.get_stock_high_low_price(previous_date, "HIGH", days=days)
        low_price = symbol.get_stock_high_low_price(previous_date, "LOW", side="lowest", days=days)
        data = {
            "high_price": high_price,
            "high_trigger_price": trigger_price(high_price, "HIGH"),
            "low_price": low_price,
            "low_trigger_price": trigger_price(low_price, "LOW")
        }
        redis_cache.set(cache_key, data, 9*60*60)
    return True


# def func(message):
#     print(message)