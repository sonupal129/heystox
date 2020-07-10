from market_analysis.imports import *
from market_analysis.models import Strategy, StrategyTimestamp, Symbol
# CODE Below

class BaseStrategyTask(celery_app.Task):
    ignore_result = False
    queue = "high_priority"
    name = "base_strategy"
    strategy_type = "Entry"
    strategy_priority = "Primary"

    
    def create_dataframe(self, data:str, backtest=False, **kwargs):
        """Create pandas dataframe for backtesting and live analysis only
        Parameter:
        data : Json Data"""
        mandatory_keys = ["symbol", "with_live_candle"]

        if backtest:
            try:
                df = pd.read_json(data)
                return df
            except:
                raise JSONDecodeError ("Passed data type is not json data")
        
        elif not backtest:
            for key in mandatory_keys:
                if key not in kwargs.keys():
                    raise AttributeError(f"{key} field is not in kwargs, Please send {key} with kwargs")
            symbol = kwargs.get("symbol")
            with_live_candle = kwargs.get("with_live_candle", False)
            if not isinstance(symbol, Symbol):
                raise TypeError(f"{symbol} if not {Symbol} class object")
            
            df = symbol.get_stock_live_data(with_live_candle=with_live_candle, candle_type=kwargs.get("candle_type", "M5"))
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

    def base_strategy(self, stock_id, entry_type, backtest, backtesting_candles_data=None):
        pass

    def run(self, stock_id, entry_type, backtest=False, backtesting_candles_data=None, **kwargs):
        strategy_function = None
        try:
            strategy_function = getattr(self.__class__, self.name)
        except:
            return f"Strategy function name and task name should be same"
        output = strategy_function(self, stock_id, entry_type, backtest, backtesting_candles_data, **kwargs)
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

    