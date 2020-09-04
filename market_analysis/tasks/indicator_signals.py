from market_analysis.imports import *
from market_analysis.tasks.orders import EntryOrder
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.models import StrategyTimestamp, OrderBook
from market_analysis.tasks.trading import get_upstox_user
# CODE Below 
# Signal Router for Routing Order Data Processing as per Strategy

class SignalRouter:
    """Signal router route to the correct entry signal by strategy name for ex let say if we strategy 
    find a signal and before making entry entry into that stock we wanted to make sure using few additional
    function let say sell and buy quantity ratio or volumen calculation for that we can ccreate a signal for that based on that 
    strategy and router will route/ call that signal only to doing this we need to make sure that signal name should be Strategy Name + Router"""

    def __init__(self, timestamp):
        self.timestamp = timestamp

    def get_strategy_name(self):
        return self.timestamp.strategy.strategy.get_strategy().__name__

    def find_router_for_strategy(self):
        strategy_name = self.get_strategy_name()
        router_name = strategy_name + "SignalTask"
        func_module = importlib.import_module(self.__module__)
        try:
            st_func = getattr(func_module, router_name)
        except:
            st_func = getattr(func_module, "GlobalSignalTask")
            slack_message_sender.delay(text=f"No custom signal found for strategy {strategy_name} & symbol {self.timestamp.stock} with {self.timestamp.stock.entry_type} entry, Calling {st_func.__name__}")
        return st_func()

    def route_signal(self):
        max_order_place_time = settings.ORDER_PLACE_END_TIME 
        current_time = get_local_time().time()
        if current_time < max_order_place_time:
            signal = self.find_router_for_strategy()
            return signal.delay(self.timestamp.id)
        slack_message_sender.delay(text=f"Order place time ended, order can't place after {max_order_place_time}")
        return False


# Custom Signal Tasks for Every Strategy
class BaseSignalTask(celery_app.Task):
    ignore_result = False
    name = "base_signal_task"
    queue = "high_priority"
    order_place_start_time = settings.ORDER_PLACE_START_TIME
    order_place_end_time = settings.ORDER_PLACE_END_TIME


    def prepare_orderdata(self, timestamp): 
        sorted_stock = timestamp.stock
        order_detail = {}
        order_detail["name"] = sorted_stock.symbol.symbol
        order_detail["entry_time"] = timestamp.timestamp
        order_detail["entry_type"] = sorted_stock.entry_type
        order_detail["entry_price"] = int(timestamp.entry_price)
        return order_detail

    def base_signal_task(self, timestamp):
        return True

    def check_entry(self, timestamp):
        sorted_stock = timestamp.stock
        entry_price = None
        entry_available = False
        
        if is_time_between_range(timestamp.timestamp, 20):
            last_traded_price = sorted_stock.symbol.get_stock_live_price(price_type="ltp")
            if sorted_stock.entry_type == "BUY" and timestamp.entry_price > last_traded_price:
                entry_price = last_traded_price
            elif sorted_stock.entry_type == "SELL" and timestamp.entry_price < last_traded_price:
                entry_price = last_traded_price
            try:
                existing_order = OrderBook.objects.get(symbol=sorted_stock.symbol, date=get_local_time().date())
                last_order = existing_order.get_last_order_by_status()
                if last_order.entry_type == "EX":
                    entry_available = True
            except:
                entry_available = True
            if entry_available:
                if entry_price:
                    sorted_stock.entry_price = entry_price
                    timestamp.entry_price = entry_price
                timestamp.save()
                sorted_stock.save()
        else:
            slack_message_sender.delay(text=f"Stock Entry Time is Out of Limit Could Not Place Order for {sorted_stock}", channel="#random")
        return entry_available

    def run(self, timestamp_id):
        timestamp = StrategyTimestamp.objects.get(id=timestamp_id)
        entry_available = self.check_entry(timestamp)
        current_time = get_local_time().time()

        signal_function = None
        sleep(0.3)
        try:
            signal_function = getattr(self.__class__, self.name)
        except:
            raise AttributeError("Function name should be same as name attribute")
        
        if current_time > self.order_place_start_time and current_time < self.order_place_end_time:
            if (signal_function(self, timestamp) and entry_available) == True:
                order_data = self.prepare_orderdata(timestamp)
                EntryOrder().delay(order_data, strategy_id=timestamp.strategy.id)
                return {"success": True}
        slack_message_sender.delay(text=f"Order can be place between {self.order_place_start_time} and {self.order_place_end_time}")
        return {"success": False, "errors": "Entry Condition Not Fulfilled"}
        


class GlobalSignalTask(BaseSignalTask):
    """This is Global Signal Task which will work if no individual signal task found for strategy,
    Inherited data from Base Signal Task"""
    name = "global_signal_tasks"

    def global_signal_tasks(self, timestamp):
        user = get_upstox_user()
        symbol = timestamp.stock.symbol
        sorted_stock = timestamp.stock
        user.get_master_contract(symbol.exchange.name.upper())
        data = user.get_live_feed(user.get_instrument_by_symbol(symbol.exchange.name.upper(), symbol.symbol.upper()), LiveFeedType.Full)
        percentage_calculator = lambda higher_number, lower_number : (higher_number - lower_number) / lower_number * 100
        buy_qty = data["total_buy_qty"]
        sell_qty = data["total_sell_qty"]
        if (sorted_stock.entry_type == "BUY" and percentage_calculator(buy_qty, sell_qty)) or (sorted_stock.entry_type == "SELL" and percentage_calculator(sell_qty, buy_qty)) >= -30:
            return True
        else:
            return False

celery_app.tasks.register(GlobalSignalTask)

class RangeReversalStrategySignalTask(GlobalSignalTask):
    name = "range_reversal_signal_task"
    order_place_start_time = time(9,21)
    order_place_end_time = time(12,59)

    def range_reversal_signal_task(self, timestamp):
        return True

celery_app.tasks.register(RangeReversalStrategySignalTask)





