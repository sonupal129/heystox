from market_analysis.imports import *
from market_analysis.models import Strategy, StrategyTimestamp
# CODE Below

class BaseStrategyTask(celery_app.Task):
    ignore_result = False
    queue = "high_priority"
    name = "base_strategy"
    strategy_type = "Entry"
    strategy_priority = "Primary"

    
    def create_backtesting_dataframe(self, json_data:str):
        """Create pandas dataframe for backtesting only
        Parameter:
        json_data : pandas dataframe data in json format"""
        if not isinstance(json_data, str):
            raise TypeError("json_data is not type of Json data string")
        try:
            df = pd.read_json(json_data)
        except:
            raise JSONDecodeError ("Passed data type is not Json Data")
        return df

    def check_strategy_priority(self):
        if self.strategy_type == "Entry" and not self.strategy_priority:
            raise AttributeError("Attribute strategy_priority not Defined")

    def create_indicator_timestamp(self, stock, entry_type, entry_price:float, entry_time:object, backtest=False, time_range:int=20):
        """This function create timestamp object if signal found using strategy, or if it's backtest parameter is true
        it return only object data do not create any timestamp"""
        if backtest:
            context = {
                "symbol_name" : stock.symbol,
                "strategy_name" : self.__class__.__name__,
                "entry_price" : entry_price,
                "entry_time" : entry_time
            }
            return context
        else:
            strategy = Strategy.objects.get(strategy_name=self.__class__.__name__, strategy_location=self.__class__.__module__, strategy_type="ET" if self.strategy_type == "Entry" else "EX")
            sorted_stock = stock.get_sorted_stock(entry_type)
            stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, strategy=strategy, timestamp__range=[entry_time - timedelta(minutes=time_range), entry_time + timedelta(minutes=time_range)]).order_by("timestamp")
            if not stamp.exists():
                stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, strategy=strategy, timestamp=entry_time)
                stamp.entry_price = entry_price
                stamp.save()
            elif stamp.count() > 1:
                stamp.exclude(id=stamp.first().id).delete()
            return "Signal Found"

    def base_strategy(self, stock_id, entry_type, backtest, backtesting_json_data_frame=None):
        pass

    def run(self, stock_id, entry_type, backtest=False, backtesting_json_data_frame=None):
        strategy_function = None
        try:
            strategy_function = getattr(self.__class__, self.name)
        except:
            return f"Strategy function name and task name should be same"
        output = strategy_function(self, stock_id, entry_type, backtest, backtesting_json_data_frame)
        if backtest and not isinstance(output, str):
            return self.create_indicator_timestamp(*output)


class BaseEntryStrategy(BaseStrategyTask):
    pass


class BaseExitStrategy(BaseStrategyTask):
    strategy_type = "Exit"

    def create_indicator_timestamp(self, stock, entry_type, entry_price:float, entry_time:object, backtest=False, time_range:int=20):
        """This function create timestamp object if signal found using strategy, or if it's backtest parameter is true
        it return only object data do not create any timestamp"""
        if backtest:
            context = {
                "symbol_name" : stock.symbol,
                "strategy_name" : self.__class__.__name__,
                "entry_price" : entry_price,
                "entry_time" : entry_time
            }
            return context
        else:
            # Need to work more on it 
            strategy = Strategy.objects.get(strategy_name=self.__class__.__name__, strategy_location=self.__class__.__module__, strategy_type="ET" if self.strategy_type == "Entry" else "EX")
            sorted_stock = stock.get_sorted_stock(entry_type)
            stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, strategy=strategy, timestamp__range=[entry_time - timedelta(minutes=time_range), entry_time + timedelta(minutes=time_range)]).order_by("timestamp")
            if not stamp.exists():
                stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, strategy=strategy, timestamp=entry_time)
                stamp.entry_price = entry_price
                stamp.save()
            elif stamp.count() > 1:
                stamp.exclude(id=stamp.first().id).delete()
            return "Signal Found"

    