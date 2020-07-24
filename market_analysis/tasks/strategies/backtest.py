from market_analysis.imports import *
from market_analysis.models import Strategy, Symbol, BacktestReport
from market_analysis.tasks.trading import get_liquid_stocks
# Code Start Below


# Backtesting Function
class BaseBackTestStrategy(celery_app.Task):
    """Backtesting Base task with base requesired functions which will be used while backtesting,
    Prepare data for backtesting"""
    ignore_result = False
    queue = "strategy"
    name = "base_backtest_strategy"

    def check_mandatory_fields(self, fields_list:list, mandatory_fields:list=['symbol_name', "strategy_name", 'entry_price', 'entry_time', 'stoploss',
                                'target', 'strategy_status', 'exit_price', 'exit_time', 'pl']):
        """Checks mandatory fields in dataframe"""
        for field in mandatory_fields:
            if field not in fields_list:
                raise AttributeError(f"Dataframe has not required field {field} in it")
    
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

    def add_backtest_data(self, dataframe, **kwargs):
        """Added backtesting data in table so next time don't need to run function again to fetch data"""
        backtest_rows = []
        last_row = dataframe.iloc[-1]
        create_report = False
        self.check_mandatory_fields(kwargs.keys(), ["entry_type", "candle_type"])
        entry_type = kwargs.get("entry_type")
        candle_type = kwargs.get("candle_type")
        reports = BacktestReport.objects.filter(symbol_name=last_row.symbol_name, strategy_name=last_row.strategy_name,
                                                entry_type=entry_type, candle_type=candle_type)
        if reports.exists():
            dataframe = dataframe.loc[dataframe["entry_time"] > reports.last().entry_time]
            if not dataframe.empty:
                create_report = True
        elif not reports.exists():
                create_report = True
        if create_report:
            for index, row in dataframe.iterrows():
                backtest_rows.append(BacktestReport(symbol_name=row["symbol_name"], stoploss=row["stoploss"],
                                    strategy_name=row["strategy_name"], target=row["target"],
                                    entry_price=row["entry_price"], entry_time=row["entry_time"],
                                    strategy_status=row["strategy_status"], exit_price=row["exit_price"],
                                    exit_time=row["exit_time"], pl=row["pl"], entry_type=entry_type,
                                    candle_type=candle_type))
            BacktestReport.objects.bulk_create(backtest_rows)

    def get_strategy(self, strategy):
        """get callable function which is stored in dtabase as string"""
        func_module = importlib.import_module(strategy.strategy_location)
        st_func = getattr(func_module, strategy.strategy_name)
        if callable(st_func):
            return st_func()
        raise TypeError("Provided strategy is not callable please check strategy location again!")

    def create_cache_key(self, obj_list:list):
        return "_".join(str(i) for i in obj_list)

    def prepare_backtesting_data(self, **kwargs):
        """Prepare data for backtesting"""
        data = {
        "entry_type" : kwargs.get("entry_type"),
        "symbol" : Symbol.objects.get(id=int(kwargs.get("stock_id"))),
        "end_date" : datetime.strptime(kwargs.get("end_date"), "%Y-%m-%d").date(),
        "to_days" : kwargs.get("to_days"),
        "candle_type" : kwargs.get("candle_type"),
        "strategy" : Strategy.objects.get(id=int(kwargs.get("strategy_id"))),
        "task_cache_key": self.create_cache_key([*kwargs.values(),"temp_backtest_tasks_data"]),
        "form_cache_key": kwargs.get("cache_key", "no_key")
        }
        return data
    
    def run(self, **kwargs):
        pass


class CalculateBackTestEquityIntrdayData(BaseBackTestStrategy):
    """Backtesting strategy for equity intraday stocks, get data from redis cache and then calculate and filter that 
    data for intraday purpose, it gets data from SendBacktest request class function"""

    name = "calculate_intraday_strategies_data"
    queue = "tickers"
    
    def calculate_backtest_data(self, cache_key, entry_type, **kwargs):
        cached_value = cache.get(cache_key)
        success_tasks = [task.result for task in cached_value if isinstance(task.result, dict)]
        strategy_output_df = pd.DataFrame(success_tasks)
        candles_df = pd.read_json(kwargs.get("candles_df"))
        if not strategy_output_df.empty:
            strategy_output_df = strategy_output_df.drop_duplicates(subset="entry_time")
            strategy_output_df["stoploss"] = [get_stock_stoploss_price(price, entry_type) for price in strategy_output_df.entry_price]
            strategy_output_df["target"] = [get_stock_target_price(price, entry_type) for price in strategy_output_df.entry_price]
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
                if entry_type == "BUY":
                    stoploss_row = df.loc[df["low_price"] <= d.stoploss].head(1)
                    target_row = df.loc[df["high_price"] >= d.target].head(1)
                elif entry_type == "SELL":
                    stoploss_row = df.loc[df["high_price"] >= d.stoploss].head(1)
                    target_row = df.loc[df["low_price"] <= d.target].head(1)
                exit_row = self.compare_target_stoploss_diffrent(target_row, stoploss_row)
                if exit_row:
                    if exit_row.get("hit") == "TARGET":
                        exit_price.append(d.target)
                    elif exit_row.get("hit") == "STOPLOSS":
                        exit_price.append(d.stoploss)
                    strategy_status.append(exit_row.get("hit"))
                    exit_timing.append(exit_row["date"])
                else:
                    strategy_status.append("SIDEWAYS")
                    try:
                        last_trading_row = df.loc[df["date"] >= str(exit_date_time)].iloc[0]
                        exit_price.append(last_trading_row.close_price)
                        exit_timing.append(last_trading_row.date)
                    except:
                        exit_price.append(d.entry_price)
                        exit_timing.append("No Time Found")
            
            strategy_output_df["strategy_status"] = strategy_status
            strategy_output_df["exit_price"] = exit_price
            strategy_output_df["exit_time"] = exit_timing
            if entry_type == "SELL":
                strategy_output_df["pl"] = strategy_output_df["entry_price"] - strategy_output_df["exit_price"]
            elif entry_type == "BUY":
                strategy_output_df["pl"] = strategy_output_df["exit_price"] - strategy_output_df["entry_price"]
            if len(strategy_output_df) > 5:
                strategy_output_df = strategy_output_df.loc[(strategy_output_df.entry_time - strategy_output_df.entry_time.shift()) >= pd.Timedelta(minutes=20)]
            strategy_output_df = strategy_output_df.drop("time", axis=1)
            strategy_output_df = strategy_output_df.loc[strategy_output_df["entry_price"] != strategy_output_df["exit_price"]]

            filtered_rows = []
            for index, row in strategy_output_df.iterrows():
                if len(filtered_rows) >= 1:
                    if filtered_rows[-1].exit_time <= row["entry_time"]:
                        filtered_rows.append(row)
                else:
                    filtered_rows.append(row)
            strategy_output_df = pd.DataFrame(filtered_rows)
            cache.delete(cache_key)
            redis_cache.delete(kwargs.get("form_cache_key", "no_key") + "_requested")   
        return strategy_output_df

    def run(self, **kwargs):
        backtesting_df = self.calculate_backtest_data(**kwargs)
        if not backtesting_df.empty:
            self.check_mandatory_fields(backtesting_df.columns)
            self.add_backtest_data(backtesting_df, **kwargs)
            return True

celery_app.tasks.register(CalculateBackTestEquityIntrdayData)

class SendBackTestingRequest(BaseBackTestStrategy):
    """This functions send data request for strategy function with backtesting true parameter
    so strategy function can apply strat4egy on that function but  will not store data in database
    instead that will resturn data in dict form which will be later calculated, so basically this function
    send multiple request to strategy function with diffrenty candles and that call those function using group method of celery
    and store the all result in redis"""
    queue = "strategy"
    name = "send_backtesting_data_request"

    def send_backtesting_data_request(self, **kwargs):
        strategy = self.get_strategy(kwargs.get("strategy"))
        symbol = kwargs.get("symbol")
        to_days = kwargs.get("to_days")
        end_date = kwargs.get("end_date")
        candle_type = kwargs.get("candle_type")
        entry_type = kwargs.get("entry_type")
        if candle_type in ["M30", "1H"]:
            to_days += 40
        candles = symbol.get_stock_data(days=to_days, end_date=end_date)
        candles_df = symbol.get_stock_dataframe(candles, candle_type)
        df_cache_key = generate_random_string(10)
        cache.set(df_cache_key, candles_df, 30*60)
        print("Please wait data is getting prepared for strategy...")
        output = []

        for i in range(1, len(candles_df) + 1):
            context = {"head_count": i}
            output.append(strategy.s(symbol.id, entry_type, backtest=True, backtesting_candles_cache_key=df_cache_key, **context))

        run_tasks = group(output)
        results = run_tasks.apply_async()
        cache_key = kwargs.get("task_cache_key")
        data = {
            "entry_type" : entry_type,
            "candle_type": candle_type,
            "cache_key": cache_key,
            "candles_df": candles_df.to_json(),
            "form_cache_key": kwargs.get("form_cache_key", "no_key")
        }
        cache.set(cache_key, results, 30*60) # Used File based cache to store data
        # Call A celery function which will calculate the result of response
        CalculateBackTestEquityIntrdayData().apply_async(kwargs=data, countdown=600)

    def run(self, **kwargs):
        data = self.prepare_backtesting_data(**kwargs)
        self.send_backtesting_data_request(**data)

celery_app.tasks.register(SendBackTestingRequest)

@celery_app.task(queue="medium_priority")
def create_backtesting_data_async(to_days=None, max_price=300):
    """Function will run on periodically basis start backtesting, Please use/modify this function very carefully
    as any one mistake will lead celery dead lock or database locked. this is a heavy function which call celery tasks for 
    longer time"""
    strategies = Strategy.objects.filter(backtesting_ready=True)
    liquid_stocks = get_liquid_stocks(max_price=max_price)
    current_time = get_local_time().now()
    task_counter = 0

    def get_day_count(entry_time:datetime, candle_type):
        entry_date = entry_time.date()
        today_date = get_local_time().date()
        day_count = (entry_date - today_date).days
        if candle_type in ["1H", "M30"]:
            return day_count + 10
        return day_count + 2
    
    run_task_after = 0
    for stock in liquid_stocks:
        if task_counter >= 10:
            break
        data = {
            "entry_type" : "BUY",
            "stock_id" : stock.id,
            "to_days" : to_days or 90,
            "strategy_id" : "",
            "end_date" : str(get_local_time().date())
        }
        for strategy in strategies:
            data["strategy_id"] = strategy.id
            reports = BacktestReport.objects.filter(strategy_name=strategy.strategy_name, symbol_name=stock.symbol)
            for candle_choice in strategy.timeframe:
                candle_type_report = reports.filter(candle_type=candle_choice)
                data["candle_type"] = candle_choice
                buy_reports = candle_type_report.filter(entry_type=data["entry_type"])
                if not buy_reports.exists():
                    SendBackTestingRequest().apply_async(kwargs=data, countdown=run_task_after)
                    task_counter += 1
                elif buy_reports.last().entry_time < (current_time - timedelta(7)):
                    data["to_days"] = get_day_count(buy_reports.last().entry_time, data["candle_type"])
                    SendBackTestingRequest().apply_async(kwargs=data, countdown=run_task_after)
                    task_counter += 1

                data["entry_type"] = "SELL"
                sell_reports = candle_type_report.filter(entry_type=data["entry_type"])
                if not sell_reports.exists():
                    SendBackTestingRequest().apply_async(kwargs=data, countdown=run_task_after)
                    task_counter += 1
                elif sell_reports.last().entry_time < (current_time - timedelta(7)):
                    data["to_days"] = get_day_count(sell_reports.last().entry_time, data["candle_type"])
                    SendBackTestingRequest().apply_async(kwargs=data, countdown=run_task_after)
                    task_counter += 1
                run_task_after += 120 # In seconds
    return True

@celery_app.task(queue="medium_priority")
def delete_backtesting_data(strategy_name, timeframe):
    BacktestReport.objects.filter(strategy_name=strategy_name, candle_type=timeframe).delete()
    for key in redis_cache.keys("*"):
        if strategy_name in key and timeframe in key:
            redis_cache.delete(key)
    return True