from market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol, Strategy
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender
from market_analysis.tasks.orders import *
# Start code below

# Backtesting Function
def create_backtesting_dataframe(json_data:str):
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



def compare_target_stoploss_diffrent(target_row, stoploss_row):
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


def backtest_indicator_strategy(stock_id:int, to_days:int, end_date, strategy, candle_type="M5", entry_type:str="BUY", cached=True, **kwargs):
    """"Description : Function is used to back test strategy, Indicator Strategy
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
    if not callable(strategy):
        raise TypeError("Argument strategy is not callable")
        
    symbol = Symbol.objects.get(id=stock_id)
    candles = symbol.get_stock_data(days=to_days, end_date=end_date, candle_type=candle_type).values("candle_type", "open_price", "high_price", "low_price", "close_price", "volume", "total_buy_quantity", "total_sell_quantity", "date")
    candles_backtest_df = pd.DataFrame()
    output = []
    
    print("Please wait while strategy getting backtested...")
    
    cache_key = "_".join([symbol.symbol, str(to_days), str(end_date), str(strategy.__name__), str(candle_type), entry_type, "backtest_strategy"])
    cached_value = redis_cache.get(cache_key)
    if cached_value is not None and cached:
        return cached_value
    
    for candle in candles:
        candles_backtest_df = candles_backtest_df.append(candle, ignore_index=True)
        output.append(strategy.s(stock_id, backtest=True, backtesting_json_data_frame=candles_backtest_df.to_json()))
    
    run_tasks = group(output)
    results = run_tasks.apply_async()
    sleep(20)

    while not results.ready():
        sleep(2)
    
    success_tasks = [task.result for task in results if isinstance(task.result, dict)]
    strategy_output_df = pd.DataFrame(success_tasks)
    strategy_output_df = strategy_output_df.drop_duplicates(subset="entry_time")
    strategy_output_df["stoploss"] = [get_stock_stoploss_price(price, entry_type) for price in strategy_output_df.entry_price]
    strategy_output_df["target"] = [get_stock_target_price(price, entry_type) for price in strategy_output_df.entry_price]
    
    default_exit_time = kwargs.get("default_exit_time", "14:30")
    exit_time = datetime.strptime(default_exit_time, "%H:%M")
    candles_dataframe = pd.DataFrame(list(candles))
    strategy_status = []
    exit_price = []
    
    for d in strategy_output_df.itertuples():
        df = candles_dataframe
        entry_time = datetime.strptime(d.entry_time, "%Y-%m-%dT%H:%M:%S")
        df = df.loc[df["date"] >= d.entry_time]
        df = df.loc[df["date"].dt.date.astype(str) == str(entry_time.date())]
        exit_date_time = entry_time.replace(hour=exit_time.hour, minute=exit_time.minute)

        if entry_type == "BUY":
            stoploss_row = df.loc[df["low_price"] <= d.stoploss].head(1)
            target_row = df.loc[df["high_price"] >= d.target].head(1)
        elif entry_type == "SELL":
            stoploss_row = df.loc[df["high_price"] >= d.stoploss].head(1)
            target_row = df.loc[df["low_price"] <= d.target].head(1)
        exit_row = compare_target_stoploss_diffrent(target_row, stoploss_row)

        if exit_row:
            if exit_row.get("hit") == "TARGET":
                exit_price.append(d.target)
            elif exit_row.get("hit") == "STOPLOSS":
                exit_price.append(d.stoploss)
            strategy_status.append(exit_row.get("hit"))

        else:
            strategy_status.append("SIDEWAYS")
            last_trading_row = df.loc[df["date"] >= str(exit_date_time)].iloc[0]
            exit_price.append(last_trading_row.close_price)
    
    strategy_output_df["strategy_status"] = strategy_status
    strategy_output_df["exit_price"] = exit_price
    if entry_type == "SELL":
        strategy_output_df["p/l"] = strategy_output_df["entry_price"] - strategy_output_df["exit_price"]
    elif entry_type == "BUY":
        strategy_output_df["p/l"] = strategy_output_df["exit_price"] - strategy_output_df["entry_price"]          
    
    strategy_output_df["entry_time"] = pd.to_datetime(strategy_output_df.entry_time, format="%Y-%m-%dT%H:%M:%S")
    strategy_output_df = strategy_output_df.loc[(strategy_output_df.entry_time - strategy_output_df.entry_time.shift()) >= pd.Timedelta(minutes=20)]
    redis_cache.set(cache_key, strategy_output_df, 80*30)
    return strategy_output_df


@celery_app.task(queue="medium_priority")
def prepare_n_call_backtesting_strategy(*args, **kwargs):
    data = {
        "entry_type" : kwargs.get("entry_type"),
        "stock_id" : kwargs.get("stock_id"),
        "end_date" : datetime.strptime(kwargs.get("end_date"), "%Y-%m-%d").date(),
        "to_days" : kwargs.get("to_days"),
        "candle_type" : kwargs.get("candle_type")
    }
    strategy_id = kwargs.get("strategy_id")
    strategy = Strategy.objects.get(id=strategy_id)
    func_module = importlib.import_module(strategy.strategy_location)
    st_func = getattr(func_module, strategy.strategy_name)
    data["strategy"] = st_func
    backtest_indicator_strategy(**data)
    redis_cache.set(kwargs.get("form_cache_key"), True, 60*3)
    return "Backtesting Completed!, Run function again to get output"
    



# STRATEGY GUIDELINES
# 1. Strategy works on three indicator type Primary, Secondary or Support Indicators
# 2. Primary Indicator mean if supporting indicator and secondary are with primary indicator then well n good else take entry basis or primary indicator only
# 3. Secondary indicator can only take entry if there is 2 or more supporting indicators available with it
# 4. Please do not make any change backtest function unless it is required
# 5. There is a way to right strategy, So please understand previouse strategy function parameter then implement new strategy

# Timestamp Creater
def create_indicator_timestamp(stock, entry_type, indicator_name:str, entry_price:float, entry_time:object, backtest=False, time_range:int=20):
    """This function create timestamp object if signal found using strategy, or if it's backtest parameter is true
    it return only object data do not create any timestamp"""
    if backtest:
        context = {
            "symbol_name" : stock.symbol,
            "indicator_name" : indicator_name,
            "entry_price" : entry_price,
            "entry_time" : entry_time
        }
        return context
    
    indicator = Indicator.objects.get(name=indicator_name)
    sorted_stock = stock.get_sorted_stock(entry_type)
    stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=indicator, timestamp__range=[entry_time - timedelta(minutes=time_range), entry_time + timedelta(minutes=time_range)]).order_by("timestamp")
    if not stamp.exists():
        stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=indicator, timestamp=entry_time)
        stamp.entry_price = entry_price
        stamp.save()
    elif stamp.count() > 1:
        stamp.exclude(id=stamp.first().id).delete()
    return "Signal Found"


# Strategies

# Strategy Registery
def register_strategy(function):
    """Function register strategy on strategy model"""
    
    @functools.wraps(function)
    def wraper(*args, **kwargs):
        function_cache_key = ".".join([function.__module__, function.__name__])
        cached_value = redis_cache.get(function_cache_key)
        if cached_value == None:         
            is_strategy, created = Strategy.objects.get_or_create(strategy_location=function.__module__, strategy_name=function.__name__)
            redis_cache.set(function_cache_key, is_strategy, 30*60*48)
        return function(*args, **kwargs)
    wraper.__newname__ = function.__name__
    return wraper


@celery_app.task(queue="low_priority")
def find_ohl_stocks():
    """Based on Open high low strategy, it is supporting strategy only"""
    current_time = get_local_time().time()
    start_time = time(9,25)
    if current_time > start_time:
        cache_key = str(get_local_time().date()) + "_todays_sorted_stocks"
        sorted_stocks = redis_cache.get(cache_key)
        if sorted_stocks:
            todays_timestamps = StrategyTimestamp.objects.select_related("stock", "indicator").filter(indicator__name="OHL", timestamp__date=get_local_time().date())
            for stock in sorted_stocks:
                timestamps = todays_timestamps.filter(stock=stock)
                ohl_condition = stock.symbol.is_stock_ohl()
                if ohl_condition:
                    if stock.entry_type == ohl_condition and not timestamps.exists():
                        ohl_indicator = Indicator.objects.get(name="OHL")
                        StrategyTimestamp.objects.create(indicator=ohl_indicator, stock=stock, timestamp=get_local_time().now())
                    elif stock.entry_type != ohl_condition:
                        timestamps.delete()
                    elif timestamps.count() > 1:
                        timestamps.exclude(id=timestamps.first().id).delete()
            return "OHL Updated"
        return "No Sorted Stocks Cached"
    return f"Time {current_time} not > 9:25"


@celery_app.task(queue="low_priority") # Will Work on These Functions Later
def is_stock_pdhl(obj_id): 
    """Based on previouse day high low strategy, supporting strategy"""
    stock = SortedStocksList.objects.get(id=obj_id)
    if stock.symbol.is_stock_pdhl() == stock.entry_type:
        pdhl_indicator = Indicator.objects.get(name="PDHL")
        pdhl, is_created = StrategyTimestamp.objects.get_or_create(indicator=pdhl_indicator, stock=stock)
        pdhl.timestamp = get_local_time().now()
        pdhl.save()
        return "Stamp Created"

@celery_app.task(queue="low_priority") # Will Work on These Functions Later
def has_entry_for_long_short(obj_id):
    """Entry available of long or short position, Supporting strategy"""
    stock = SortedStocksList.objects.get(id=obj_id)
    if stock.symbol.has_entry_for_long_short() == stock.entry_type:
        long_short_entry = Indicator.objects.get(name="LONGSHORT")
        long_short, is_created = StrategyTimestamp.objects.get_or_create(indicator=long_short_entry, stock=stock)
        long_short.timestamp = get_local_time().now()
        long_short.save()

@celery_app.task(queue="high_priority")
@register_strategy
def find_stochastic_bollingerband_crossover(stock_id, entry_type="BUY", backtest=False, backtesting_json_data_frame=None):
    """Find Bollinger crossover with adx and stochastic crossover, Supporting Strategy"""
    stock = Symbol.objects.get(id=stock_id)
    today_date = get_local_time().date()
    
    if backtest:
        df = create_backtesting_dataframe(backtesting_json_data_frame)
    else:
        df = stock.get_stock_live_data(with_live_candle=False)
    
    df["medium_band"] = bollinger_mavg(df.close_price)
    df["adx"] = adx(df.high_price, df.low_price, df.close_price)
    df = df.drop(columns=["total_buy_quantity", "total_sell_quantity"])
    df["medium_band"] = df.medium_band.apply(roundup)
    df["bollinger_signal"] = np.where(df.close_price < df.medium_band, "SELL", "BUY")
    if not backtest:
        df = df.loc[df["date"] > str(today_date)]
    df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "BUY"), "bollinger_signal"] = "BUY_CROSSOVER"
    df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "SELL"), "bollinger_signal"] = "SELL_CROSSOVER"
    bollinger_df = df.copy(deep=True).drop(df.head(1).index)
        
    try:
        if entry_type == "SELL":
            bollinger_crossover = bollinger_df[bollinger_df.bollinger_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif entry_type == "BUY":
            bollinger_crossover = bollinger_df[bollinger_df.bollinger_signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
    except:
        bollinger_crossover = pd.Series()
        
    if not bollinger_crossover.empty:
        try:
            candle_before_crossover = bollinger_df.loc[bollinger_df["date"] < bollinger_crossover.date].iloc[-1]
            candle_after_crossover = bollinger_df.loc[bollinger_df["date"] > bollinger_crossover.date].iloc[0]
        except:
            return "Candle Before and After Could not be Created"

        bollinger_signal = pd.Series()
        
        if entry_type == "BUY":
            if (candle_before_crossover.open_price <= bollinger_crossover.medium_band and candle_before_crossover.close_price <= bollinger_crossover.medium_band) and \
                (candle_after_crossover.open_price > bollinger_crossover.medium_band or candle_after_crossover.close_price > bollinger_crossover.medium_band):
                bollinger_signal = candle_after_crossover

        elif entry_type == "SELL":
            if (candle_before_crossover.open_price >= bollinger_crossover.medium_band and candle_before_crossover.close_price >= bollinger_crossover.medium_band) and \
                (candle_after_crossover.open_price < bollinger_crossover.medium_band or candle_after_crossover.close_price < bollinger_crossover.medium_band):
                bollinger_signal = candle_after_crossover

        if not bollinger_signal.empty:
            #Stochastic Indicator 
            df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
            df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
            df["stochastic_signal"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
            df.loc[(df["stochastic_signal"].shift() == "BUY") & (df["stochastic_signal"] == "SELL") & (df["stochastic_signal"].shift(-1) == "BUY"), "stochastic_signal"] = "BUY"
            df.loc[(df["stochastic_signal"].shift() == "SELL") & (df["stochastic_signal"] == "BUY") & (df["stochastic_signal"].shift(-1) == "SELL"), "stochastic_signal"] = "SELL"
            df.loc[(df["stochastic_signal"] != df["stochastic_signal"].shift()) & (df["stochastic_signal"] == "BUY"), "stochastic_signal"] = "BUY_CROSSOVER"
            df.loc[(df["stochastic_signal"] != df["stochastic_signal"].shift()) & (df["stochastic_signal"] == "SELL"), "stochastic_signal"] = "SELL_CROSSOVER"
            stoch_df = df.loc[df["date"]  <= bollinger_crossover.date]

            try:
                if entry_type == "SELL":
                    stochastic_crossover = stoch_df[stoch_df.stochastic_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
                elif entry_type == "BUY":
                    stochastic_crossover = stoch_df[stoch_df.stochastic_signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
            except:
                stochastic_crossover = pd.Series()
            
            if not stochastic_crossover.empty:
                time_diff = bollinger_signal.date - stochastic_crossover.date
                if time_diff <= timedelta(minutes=25) and bollinger_signal.adx <= 23:
                    response = create_indicator_timestamp(stock, entry_type, "STOCHASTIC_BOLLINGER", float(bollinger_signal.close_price), bollinger_signal.date, backtest, 20)  
                    return response
            return "Stochastic Crossover Not Found"
        return "Bollinger Signal Not Found"
    return "Bollinger Crossover Not Found"
    

@celery_app.task(queue="medium_priority")
@register_strategy
def find_stochastic_macd_crossover(stock_id, entry_type, backtest=False, backtesting_json_data_frame=None):
    """(Custom Macd Crossover) This function find crossover between macd and macd signal and return signal as buy or sell"""
    stock = Symbol.objects.get(id=stock_id)
    today_date = get_local_time().date()
    df = stock.get_stock_live_data()
    if backtest:
        df = create_backtesting_dataframe(backtesting_json_data_frame)
    
    df["macd"] = macd(df.close_price)
    df["macd_signal"] = macd_signal(df.close_price)
    df["macd_diff"] = macd_diff(df.close_price)
    df["percentage"] = round(df.macd * df.macd_diff /100, 6)
    df["macd_crossover"] = np.where(df.macd < df.macd_signal, "SELL", "BUY")
    df.loc[(df["macd_crossover"] != df["macd_crossover"].shift()) & (df["macd_crossover"] == "BUY"), "macd_crossover"] = "BUY_CROSSOVER"
    df.loc[(df["macd_crossover"] != df["macd_crossover"].shift()) & (df["macd_crossover"] == "SELL"), "macd_crossover"] = "SELL_CROSSOVER"
    df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
    df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
    df["stoch_diff"] = df.stoch - df.stoch_signal
    df["percentage"] = round(df.stoch * (df.stoch - df.stoch_signal) /100, 6)
    df["stochastic_crossover"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
    df.loc[(df["stochastic_crossover"].shift() == "BUY") & (df["stochastic_crossover"] == "SELL") & (df["stochastic_crossover"].shift(-1) == "BUY"), "stochastic_crossover"] = "BUY"
    df.loc[(df["stochastic_crossover"].shift() == "SELL") & (df["stochastic_crossover"] == "BUY") & (df["stochastic_crossover"].shift(-1) == "SELL"), "stochastic_crossover"] = "SELL"
    df.loc[(df["stochastic_crossover"] != df["stochastic_crossover"].shift()) & (df["stochastic_crossover"] == "BUY"), "stochastic_crossover"] = "BUY_CROSSOVER"
    df.loc[(df["stochastic_crossover"] != df["stochastic_crossover"].shift()) & (df["stochastic_crossover"] == "SELL"), "stochastic_crossover"] = "SELL_CROSSOVER"
    df = df.drop(columns=["total_buy_quantity", "total_sell_quantity"])
    if not backtest:
        df = df.loc[df["date"] > str(today_date)]
    
    new_df = df.copy(deep=True).drop(df.tail(1).index)
    
    try:
        if entry_type == "SELL":
            macd_crossover = new_df[new_df.macd_crossover.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif entry_type == "BUY":
            macd_crossover = new_df[new_df.macd_crossover.str.endswith("BUY_CROSSOVER")].iloc[-1]
    except:
        macd_crossover = pd.Series()


    if not macd_crossover.empty:
        df_after_last_crossover = df.loc[df["date"] > macd_crossover.date]
        try:
            if macd_crossover.macd_crossover == "SELL_CROSSOVER":
                macd_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.macd_diff <= -0.070)].iloc[0]
            elif macd_crossover.macd_crossover == "BUY_CROSSOVER":
                macd_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.macd_diff >= 0.070)].iloc[0]
        except:
            macd_crossover_signal = pd.Series()
        

        if not macd_crossover_signal.empty:
            df = df.loc[df["date"] < macd_crossover.date]
            try:
                if entry_type == "SELL":
                    stochastic_crossover = df[df.stochastic_crossover.str.endswith("SELL_CROSSOVER")].iloc[-1]
                elif entry_type == "BUY":
                    stochastic_crossover = df[df.stochastic_crossover.str.endswith("BUY_CROSSOVER")].iloc[-1]
            except:
                stochastic_crossover = pd.Series()
                
            if not stochastic_crossover.empty:
                df_after_last_crossover = df.loc[df["date"] >= stochastic_crossover.date]
                try:
                    if stochastic_crossover.stochastic_crossover == "SELL_CROSSOVER":
                        stochastic_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.stoch_diff <= -20.05)].iloc[-1]
                    elif stochastic_crossover.stochastic_crossover == "BUY_CROSSOVER":
                        stochastic_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.stoch_diff >= 22.80)].iloc[-1]
                except:
                    stochastic_crossover_signal = pd.Series()
                
                if not stochastic_crossover_signal.empty:
                    time_diff = (macd_crossover_signal.date - stochastic_crossover_signal.date)
                    if time_diff < timedelta(minutes=30):
                        response = create_indicator_timestamp(stock, entry_type, "STOCHASTIC_MACD", macd_crossover_signal.close_price, macd_crossover_signal.date, backtest, 10)
                        return response
                return "Stochastic Signal not Found"
            return "Stochastic Crossover not Found"
        return "Macd Signal not Found"
    return "Macd Crossover not Found"


@celery_app.task(queue="medium_priority")
@register_strategy
def find_adx_bollinger_crossover(stock_id, entry_type, backtest=False, backtesting_json_data_frame=None):
    """Find bolling corssover with help of adx"""
    stock = Symbol.objects.get(id=stock_id)
    today_date = get_local_time().date()
    df = stock.get_stock_live_data(with_live_candle=False)
    
    if backtest:
        df = create_backtesting_dataframe(backtesting_json_data_frame)
    
    df["high_band"] = bollinger_hband(df.close_price)
    # df["medium_band"] = bollinger_mavg(df.close_price)
    df["low_band"] = bollinger_lband(df.close_price)
    df = df.drop(columns=["total_buy_quantity", "total_sell_quantity"])
    df["adx"] = adx(df.high_price, df.low_price, df.close_price)
    df["adx_neg"] = adx_neg(df.high_price, df.low_price, df.close_price)
    df["adx_pos"] = adx_pos(df.high_price, df.low_price, df.close_price)
    
    if not backtest:
        df = df.loc[df["date"] > str(today_date)]
    
    df["bollinger_signal"] = "No Signal"
    df.loc[(df["close_price"] > df["high_band"]), "bollinger_signal"] = "SELL"
    df.loc[(df["close_price"] < df["low_band"]), "bollinger_signal"] = "BUY"
    try:
        df = df.drop(index=list(range(75,80)))
    except:
        df = pd.DataFrame()

    if not df.empty:
        try:
            if entry_type == "SELL":
                bollinger_crossover = df[df.bollinger_signal.str.endswith("SELL")].iloc[-1]
            elif entry_type == "BUY":
                bollinger_crossover = df[df.bollinger_signal.str.endswith("BUY")].iloc[-1]
        except:
            bollinger_crossover = pd.Series()

        if not bollinger_crossover.empty:
            if bollinger_crossover.adx <= 23:
                response = create_indicator_timestamp(sorted_stock, entry_type, "ADX_BOLLINGER", bollinger_crossover.close_price, bollinger_crossover.date, backtest, 15)
                return response
        return "Crossover Not Found"
    return "Dataframe not created"


@celery_app.task(queue="medium_priority")
@register_strategy
def rampat_harami(a,b):
    return a * b