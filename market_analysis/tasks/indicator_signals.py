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
            slack_message_sender.delay(text=f"No Custom signal found for strategy {strategy_name}, Calling Base Signal")
        return st_func()

    def route_signal(self):
        signal = self.find_router_for_strategy()
        return signal.delay(self.timestamp.id)


# Custom Signal Tasks for Every Strategy
class BaseSignalTask(celery_app.Task):
    ignore_result = False
    name = "base_signal_task"
    queue = "high_priority"

    def prepare_orderdata(self, timestamp):
        sorted_stock = timestamp.stock
        order_detail = {}
        order_detail["name"] = sorted_stock.symbol.symbol
        order_detail["entry_time"] = timestamp.timestamp
        order_detail["entry_type"] = sorted_stock.entry_type
        order_detail["entry_price"] = int(timestamp.entry_price)
        return order_detail

    def base_signal_task(self, timestamp):
        pass

    def update_entry_price(self, timestamp):
        sorted_stock = timestamp.stock
        entry_price = None
        
        if is_time_between_range(timestamp.timestamp, 20):
            if sorted_stock.entry_type == "BUY":
                if timestamp.entry_price == None or timestamp.entry_price > timestamp.stock.symbol.get_stock_live_price(price_type="ltp"):
                    entry_price = timestamp.stock.symbol.get_stock_live_price(price_type="ltp")
            elif sorted_stock.entry_type == "SELL":
                if timestamp.entry_price == None or timestamp.entry_price < timestamp.stock.symbol.get_stock_live_price(price_type="ltp"):
                    entry_price = timestamp.stock.symbol.get_stock_live_price(price_type="ltp")

            entry_available = False

            try:
                existing_order = OrderBook.objects.get(symbol=sorted_stock.symbol, date=get_local_time().date())
                last_order = existing_order.get_last_order_by_status()
                if last_order.entry_type == "EX":
                    entry_available = True
            except:
                existing_order = None
                entry_available = True

            sorted_stock.entry_price = entry_price if entry_price else sorted_stock.entry_price
            sorted_stock.save()
            
            if entry_available:
                return entry_available
        else:
            slack_message_sender.delay(text=f"Stock Entry Time is Out of Limit Could Not Place Order for {sorted_stock}")
            return "Crossover out of time limit"

    def run(self, timestamp_id):
        timestamp = StrategyTimestamp.objects.get(id=timestamp_id)
        self.update_entry_price(timestamp)

        signal_function = None

        try:
            signal_function = getattr(self.__class__, self.name)
        except:
            raise AttributeError("Function name should be same as name attribute")
        
        if signal_function(self, timestamp) == True:
            order_data = self.prepare_orderdata(timestamp)
            EntryOrder().delay(order_data)


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
        if sorted_stock.entry_type == "BUY" and (percentage_calculator(sell_qty, buy_qty) < 30 or percentage_calculator(buy_qty, sell_qty) > 20):
            return True
        elif sorted_stock.entry_type == "SELL" and (percentage_calculator(buy_qty, sell_qty) < 30 or percentage_calculator(sell_qty, buy_qty) > 20):
            return True
        else:
            return False

celery_app.tasks.register(GlobalSignalTask)





