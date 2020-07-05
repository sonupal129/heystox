from market_analysis.imports import *
from market_analysis.models import Strategy, Symbol
# Code Start Below


# Backtesting Function
class BackTestStrategy:

    def __init__(self, stock_id:int, to_days:int, end_date, strategy_id, candle_type="M5", entry_type:str="BUY", cached=True, **kwargs):
        """"Description : Class is used to back test strategy, Indicator Strategy
            Parameters:
            1. stock_id : stock id should be int (Symbol class Object)
            2. to_days : How many days you want to test maximum is 30 days
            3. end_date : last day of testing for ex 01 Jan to 30 Jan, So 30 Jan will be end_date, it take date object as arg
            4. strategy: Should be strategy function,
            5. candle_type: Should be string, for ex M5 or M10
            6. cached : pass bool, if true return cached data if backtested before
            7. entry_type : can be in BUY or SELL"""
        
        
        if not isinstance(stock_id, int):
            raise TypeError("Argument stock_id is not type of int")
        if not isinstance(to_days, int) or not isinstance(end_date, date):
            raise TypeError("Argument to_days or end_date is not object of interger or date")

        self.stock_id = stock_id
        self.to_days = to_days
        self.end_date = end_date
        self.strategy_id = strategy_id
        self.candle_type = candle_type
        self.entry_type = entry_type
        self.cached = cached
        self.__dict__.update(kwargs)

    def compare_target_stoploss_diffrent(self, target_row, stoploss_row):
        """Function compare compare which row came first or we can say it stoploss hit first or target hit first
        Parameter:
        target_row : dataframe filter by pandas head function head(1)
        stoploss_row : dataframe filter by pandas head function head(1)"""
        data = {}
        row = None
        if target_row.empty and stoploss_row.empty:
            return None
        elif not target_row.empty and not stoploss_row.empty:
            target_row = target_row.iloc[0]
            stoploss_row = stoploss_row.iloc[0]
            if target_row.date > stoploss_row.date:
                row = target_row
                data['hit'] = "TARGET"
            else:
                row = stoploss_row
                data['hit'] = "STOPLOSS"
        elif not target_row.empty:
            row = target_row.iloc[0]
            data["hit"] = "TARGET"
        elif not stoploss_row.empty:
            row = stoploss_row.iloc[0]
            data["hit"] = "STOPLOSS"
        else:
            return None
        if data:
            data = {**data, **row.to_dict()}
            return data

    def get_strategy(self):
        strategy = Strategy.objects.get(id=self.strategy_id)
        func_module = importlib.import_module(strategy.strategy_location)
        st_func = getattr(func_module, strategy.strategy_name)
        if callable(st_func):
            return st_func()
        raise TypeError("Provided strategy is not callable please check strategy location again!")
        
    def get_cache_key(self, symbol, strategy):
        start_date = self.end_date - timedelta(self.to_days)
        cache_key = "_".join([str(start_date), str(self.end_date), symbol.symbol, str(strategy.__name__), str(self.candle_type), self.entry_type, "backtest_strategy"])
        return cache_key

    def get_cached_value(self, symbol, strategy):
        cache_key = self.get_cache_key(symbol, strategy)
        cached_value = redis_cache.get(cache_key)
        return cached_value
    
    def run(self, **kwargs):
        strategy = self.get_strategy()    
        symbol = Symbol.objects.get(id=self.stock_id)
        candles = symbol.get_stock_data(days=self.to_days, end_date=self.end_date)
        candles_df = symbol.get_stock_dataframe(candles, self.candle_type)
        output = []
        candles_obj = []
        print("Please wait while strategy getting backtested...")
        
        cached_value = self.get_cached_value(symbol, strategy)
        if cached_value is not None and self.cached:
            return cached_value
        
        for df_index,candle in candles_df.iterrows():
            candles_obj.append(candle)
            backtest_df = pd.DataFrame(candles_obj)
            output.append(strategy.s(self.stock_id, self.entry_type, backtest=True, backtesting_candles_data=backtest_df.to_json()))
        
        run_tasks = group(output)
        results = run_tasks.apply_async()
        sleep(20)

        while not results.ready():
            sleep(2)

        success_tasks = [task.result for task in results if isinstance(task.result, dict)]
        strategy_output_df = pd.DataFrame(success_tasks)
        if not strategy_output_df.empty:
            strategy_output_df = strategy_output_df.drop_duplicates(subset="entry_time")
            strategy_output_df["stoploss"] = [get_stock_stoploss_price(price, self.entry_type) for price in strategy_output_df.entry_price]
            strategy_output_df["target"] = [get_stock_target_price(price, self.entry_type) for price in strategy_output_df.entry_price]
            default_exit_time = kwargs.get("default_exit_time", "14:30")
            exit_time = datetime.strptime(default_exit_time, "%H:%M")
            strategy_output_df["entry_time"] = pd.to_datetime(strategy_output_df.entry_time, format="%Y-%m-%dT%H:%M:%S")
            strategy_output_df["time"] = [t.time() for t in strategy_output_df.entry_time]
            strategy_output_df = strategy_output_df.loc[strategy_output_df["time"] < exit_time.time()]
            strategy_status = []
            exit_price = []
            exit_timing = []
            for d in strategy_output_df.itertuples():
                df = candles_df
                entry_time = d.entry_time
                df = df.loc[df["date"] >= d.entry_time]
                df = df.loc[df["date"].dt.date.astype(str) == str(entry_time.date())]
                exit_date_time = entry_time.replace(hour=exit_time.hour, minute=exit_time.minute)
                if self.entry_type == "BUY":
                    stoploss_row = df.loc[df["low_price"] <= d.stoploss].head(1)
                    target_row = df.loc[df["high_price"] >= d.target].head(1)
                elif self.entry_type == "SELL":
                    stoploss_row = df.loc[df["high_price"] >= d.stoploss].head(1)
                    target_row = df.loc[df["low_price"] <= d.target].head(1)
                exit_row = self.compare_target_stoploss_diffrent(target_row, stoploss_row)

                if exit_row:
                    if exit_row.get("hit") == "TARGET":
                        exit_price.append(d.target)
                    elif exit_row.get("hit") == "STOPLOSS":
                        exit_price.append(d.stoploss)
                    strategy_status.append(exit_row.get("hit"))
                    exit_timing.append(d.entry_time)

                else:
                    strategy_status.append("SIDEWAYS")
                    try:
                        last_trading_row = df.loc[df["date"] >= str(exit_date_time)].iloc[0]
                        exit_price.append(last_trading_row.close_price)
                    except:
                        exit_price.append(d.entry_price)
                    exit_timing.append(d.entry_time)
            
            strategy_output_df["strategy_status"] = strategy_status
            strategy_output_df["exit_price"] = exit_price
            strategy_output_df["exit_time"] = exit_timing
            if self.entry_type == "SELL":
                strategy_output_df["p/l"] = strategy_output_df["entry_price"] - strategy_output_df["exit_price"]
            elif self.entry_type == "BUY":
                strategy_output_df["p/l"] = strategy_output_df["exit_price"] - strategy_output_df["entry_price"]
            if len(strategy_output_df) > 5:
                strategy_output_df = strategy_output_df.loc[(strategy_output_df.entry_time - strategy_output_df.entry_time.shift()) >= pd.Timedelta(minutes=20)]
            strategy_output_df = strategy_output_df.drop("time", axis=1)
            strategy_output_df = strategy_output_df.loc[strategy_output_df["entry_price"] != strategy_output_df["exit_price"]]
        cache_key = self.get_cache_key(symbol, strategy)
        redis_cache.set(cache_key, strategy_output_df, 15*20*12*2*3)
        return strategy_output_df


@celery_app.task(queue="medium_priority")
def prepare_n_call_backtesting_strategy(*args, **kwargs):
    data = {
        "entry_type" : kwargs.get("entry_type"),
        "stock_id" : kwargs.get("stock_id"),
        "end_date" : datetime.strptime(kwargs.get("end_date"), "%Y-%m-%d").date(),
        "to_days" : kwargs.get("to_days"),
        "candle_type" : kwargs.get("candle_type"),
        "strategy_id" : kwargs.get("strategy_id")
    }
    BackTestStrategy(**data).run()
    redis_cache.delete(kwargs.get("cache_key") + "_requested")
    return "Backtesting Completed!, Run function again to get output"