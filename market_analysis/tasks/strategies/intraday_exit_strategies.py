from market_analysis.imports import *
from .base_strategy import BaseExitStrategy
from market_analysis.models import Symbol
from market_analysis.tasks.orders import ExitOrder
from market_analysis.tasks.notification_tasks import slack_message_sender
# CODE BELOW

class GlobalExitStrategy(BaseExitStrategy):
    """This is global strategy function which work on simple method where risk to reward ratio is
    1:2 mean on 1 rupee risk we are looking at 2 rupee target"""
    name = "exit_on_stoploss_target_hit"
    queue = "tickers"
   
    def exit_on_stoploss_target_hit(self, symbol_name:str):
        cache_key = "_".join([symbol_name.lower(), "cached_ticker_data"])
        cached_value = redis_cache.get(cache_key)
        stoploss_target_cache_key = "_".join([symbol_name.lower(), "stoploss_target_hit"])
        
        if cached_value != None:
            current_ticker = cached_value["stock_data"][-1]
            ltp = current_ticker["ltp"]
            stoploss = cached_value["stoploss"]
            target_price = cached_value["target_price"]
            transaction_type = cached_value["transaction_type"]
            context = {'transaction_type': cached_value["transaction_type"],
                'symbol': cached_value["symbol"],
                'order_type': 'LIMIT',
                'quantity': cached_value["quantity"],
                'price': 0.0,
                'duarion_type': 'DAY',
                'product_type': 'INTRADAY'
            }

            target_stoploss_hit = False
            order_hit = "STOPLOSS"

            if transaction_type == "BUY":
                context["transaction_type"] = "SELL"
                if ltp >= target_price: # BUY
                    context["price"] = target_price
                    # print("BUY HIt")
                    target_stoploss_hit = True
                    order_hit = "TARGET"
                elif ltp <= stoploss:
                    context["price"] = stoploss
                    context["order_type"] = "MARKET"
                    target_stoploss_hit = True
            elif transaction_type == "SELL": # SELL
                context["transaction_type"] = "BUY"
                if ltp <= target_price:
                    context["price"] = target_price
                    # print("SELL HIT")
                    order_hit = "TARGET"
                    target_stoploss_hit = True
                elif ltp >= stoploss:
                    context["price"] = stoploss
                    target_stoploss_hit = True
                    context["order_type"] = "MARKET"
                    # print("Sell SL")
            
            if target_stoploss_hit:
                if not redis_cache.get(stoploss_target_cache_key):
                    ExitOrder().delay(context, True)
                    slack_message_sender.delay(text="{0} Hit Order Sent for trade {1}".format(order_hit, symbol_name), channel="#random")
                    redis_cache.set(stoploss_target_cache_key, True)
    
    def run(self, stock_name, backtest=False, backtesting_candles_data=None):
        if backtest or backtesting_candles_data:
            raise BacktestingNotAllowedError(f"Backtesting is not allowed on {self.__class__.__name__}")
        self.exit_on_stoploss_target_hit(stock_name)

celery_app.tasks.register(GlobalExitStrategy)


#Caching Function to Cache Ticker Data in memory, This function should be last in file
class CacheTickerData:
    """Cache symbols ticker data"""
    
    def __init__(self, data:dict):
        self.data = data

    def cache_symbol_ticker_data(self):
        cache_key = "_".join([self.data["symbol"].lower(), "cached_ticker_data"])
        cached_value = redis_cache.get(cache_key)
        # print(cached_value)
        price_type = "high" if cached_value.get("transaction_type") == "BUY" else "low"
        new_price = self.data[price_type]
        if not cached_value.get(price_type):
            cached_value[price_type] = new_price
        old_price = cached_value.get(price_type)
        if price_type == "high" and new_price > old_price:
            cached_value[price_type] = new_price
        elif price_type == "low" and new_price < old_price:
            cached_value[price_type] = new_price
        context = {
                "high": self.data["high"],
                "low": self.data["low"],
                "open": self.data["open"],
                "close": self.data["close"],
                "ltp": self.data["ltp"],
                "timestamp": self.data["timestamp"][:10],
                "total_buy_qty": self.data["total_buy_qty"],
                "total_sell_qty": self.data["total_sell_qty"]
            }
        if not cached_value.get("stock_data"):
            cached_value["stock_data"] = [context]
        if self.data["ltp"] != cached_value["stock_data"][-1]["ltp"]:
            cached_value["stock_data"].append(context)
        redis_cache.set(cache_key, cached_value)
        GlobalExitStrategy().delay(self.data["symbol"].lower()) # Need to work on exit strategy and create a strategy router
        # exit_on_auto_hit_price.delay(data["symbol"].lower())
        return True

    # def run(self):
    #     self.cache_symbol_ticker_data()
    #     cache_key = "_".join([self.data["symbol"].lower(), "cached_ticker_data"])
    #     cached_value = redis_cache.get(cache_key)
    #     symbol_name = self.data["symbol"].lower()
    #     transaction_type = cached_value.get("transaction_type")
    #     symbol = Symbol.objects.get(symbol=symbol_name)
    #     sorted_stock = symbol.get_sorted_stock(transaction_type)

