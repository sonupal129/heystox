from market_analysis.imports import *
from .base_strategy import BaseExitStrategy
from market_analysis.models import Symbol
from market_analysis.tasks.orders import ExitOrder
# CODE BELOW

class GlobalExitStrategy(BaseExitStrategy):
    name = "exit_on_stoploss_target_hit"
   
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
    
    def run(self, stock_id, entry_type, backtest=False, backtesting_candles_data=None):
        if backtest or backtesting_candles_data:
            raise TypeError(f"Backtesting is not allowed on {self.__class__.__name__}")
        stock = Symbol.objects.get(id=stock_id)
        self.exit_on_stoploss_target_hit(stock.symbol)

celery_app.tasks.register(GlobalExitStrategy)
