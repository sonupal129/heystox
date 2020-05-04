from market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender

# Start code below



def create_indicator_timestamp(sorted_stock:object, indicator_name:str, entry_price:float, entry_time:object, time_range:int=20):
    indicator = indicator.objects.get(name=indicator_name)

    stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=indicator, timestamp__range=[entry_time - timedelta(minutes=time_range), entry_time + timedelta(minutes=time_range)]).order_by("timestamp")
    if not stamp.exists():
        stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=indicator, timestamp=entry_time)
        stamp.entry_price = entry_price
        stamp.save()
    elif stamp.count() > 1:
        stamp.exclude(id=stamp.first().id).delete()
    return "Signal Found"


@celery_app.task(queue="low_priority") 
def find_ohl_stocks():
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
    print(obj_id)
    stock = SortedStocksList.objects.get(id=obj_id)
    if stock.symbol.is_stock_pdhl() == stock.entry_type:
        pdhl_indicator = Indicator.objects.get(name="PDHL")
        pdhl, is_created = StrategyTimestamp.objects.get_or_create(indicator=pdhl_indicator, stock=stock)
        pdhl.timestamp = get_local_time().now()
        pdhl.save()
        return "Stamp Created"

@celery_app.task(queue="low_priority") # Will Work on These Functions Later
def has_entry_for_long_short(obj_id):
    stock = SortedStocksList.objects.get(id=obj_id)
    if stock.symbol.has_entry_for_long_short() == stock.entry_type:
        long_short_entry = Indicator.objects.get(name="LONGSHORT")
        long_short, is_created = StrategyTimestamp.objects.get_or_create(indicator=long_short_entry, stock=stock)
        long_short.timestamp = get_local_time().now()
        long_short.save()


@celery_app.task(queue="high_priority")
def find_stochastic_bolligerband_crossover(sorted_stock_id):
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = get_local_time().date()
    df = sorted_stock.symbol.get_stock_live_data()
    # Bollinger Indicators
    df["high_band"] = bollinger_hband(df.close_price)
    df["medium_band"] = bollinger_mavg(df.close_price)
    df["low_band"] = bollinger_lband(df.close_price)
    df["adx"] = adx(df.high_price, df.low_price, df.close_price)
    df = df.drop(columns=["total_buy_quantity", "total_sell_quantity"])
    df = df.loc[df["date"] > str(today_date)]
    df["high_band"] = df.high_band.apply(roundup)
    df["medium_band"] = df.medium_band.apply(roundup)
    df["low_band"] = df.low_band.apply(roundup)
    df["bollinger_signal"] = np.where(df.close_price < df.medium_band, "SELL", "BUY")
    df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "BUY"), "bollinger_signal"] = "BUY_CROSSOVER"
    df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "SELL"), "bollinger_signal"] = "SELL_CROSSOVER"
    bollinger_df = df.copy(deep=True).drop(df.head(1).index)
    bollinger_df = bollinger_df.drop(df.tail(1).index)
        
    try:
        if sorted_stock.entry_type == "SELL":
            bollinger_crossover = bollinger_df[bollinger_df.bollinger_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif sorted_stock.entry_type == "BUY":
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
        
        if sorted_stock.entry_type == "BUY":
            if (candle_before_crossover.open_price <= bollinger_crossover.medium_band and candle_before_crossover.close_price <= bollinger_crossover.medium_band) and \
                (candle_after_crossover.open_price > bollinger_crossover.medium_band or candle_after_crossover.close_price > bollinger_crossover.medium_band):
                bollinger_signal = candle_after_crossover

        elif sorted_stock.entry_type == "SELL":
            if (candle_before_crossover.open_price >= bollinger_crossover.medium_band and candle_before_crossover.close_price >= bollinger_crossover.medium_band) and \
                (candle_after_crossover.open_price < bollinger_crossover.medium_band or candle_after_crossover.close_price < bollinger_crossover.medium_band):
                bollinger_signal = candle_after_crossover

        if not bollinger_signal.empty:
            if is_time_between_range(bollinger_signal.date, get_local_time().now() - timedelta(minutes=15), get_local_time().now()):
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
                    if sorted_stock.entry_type == "SELL":
                        stochastic_crossover = stoch_df[stoch_df.stochastic_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
                    elif sorted_stock.entry_type == "BUY":
                        stochastic_crossover = stoch_df[stoch_df.stochastic_signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
                except:
                    stochastic_crossover = pd.Series()
                if not stochastic_crossover.empty:
                    time_diff = bollinger_signal.date - stochastic_crossover.date
                    if time_diff <= timedelta(minutes=25) and df.iloc[-1].adx <= 23:    
                        create_indicator_timestamp(sorted_stock, "STOCHASTIC_BOLLINGER", float(bollinger_signal.close_price), bollinger_signal.date, 40)
                return "Stochastic Crossover Not Found"
            return "Crossover is Out of time limit"
        return "Bollinger Signal Not Found"
    return "Bollinger Crossover Not Found"
    

@celery_app.task(queue="medium_priority")
def find_stochastic_macd_crossover(sorted_stock_id):
    """(Custom Macd Crossover) This function find crossover between macd and macd signal and return signal as buy or sell"""
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = get_local_time().date()
    df = sorted_stock.symbol.get_stock_live_data()
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
    df = df.loc[df["date"] > str(today_date)]
    new_df = df.copy(deep=True).drop(df.tail(1).index)
    try:
        if sorted_stock.entry_type == "SELL":
            macd_crossover = new_df[new_df.macd_crossover.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif sorted_stock.entry_type == "BUY":
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
            if is_time_between_range(macd_crossover_signal.date, get_local_time().now() - timedelta(minutes=15), get_local_time().now()):
                df = df.loc[df["date"] < macd_crossover.date]
                try:
                    if sorted_stock.entry_type == "SELL":
                        stochastic_crossover = df[df.stochastic_crossover.str.endswith("SELL_CROSSOVER")].iloc[-1]
                    elif sorted_stock.entry_type == "BUY":
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
                            create_indicator_timestamp(sorted_stock, "STOCHASTIC_MACD", macd_crossover_signal.close_price, macd_crossover_signal.date, 10)
                    return "Stochastic Signal not Found"
                return "Stochastic Crossover not Found"
            return "Crossover out of time limit"
        return "Macd Signal not Found"
    return "Macd Crossover not Found"


def find_adx_bollinger_crossover(sorted_stock_id):
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = get_local_time().date()
    df = sorted_stock.symbol.get_stock_live_data()
    df["high_band"] = bollinger_hband(df.close_price)
    df["medium_band"] = bollinger_mavg(df.close_price)
    df["low_band"] = bollinger_lband(df.close_price)
    df = df.drop(columns=["total_buy_quantity", "total_sell_quantity"])
    high_price = df["high_price"]
    close_price = df["close_price"]
    low_price = df["low_price"]
    df["adx"] = adx(high_price, low_price, close_price)
    df["adx_neg"] = adx_neg(df.high_price, df.low_price, df.close_price)
    df["adx_pos"] = adx_pos(df.high_price, df.low_price, df.close_price)
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
            if sorted_stock.entry_type == "SELL":
                bollinger_crossover = df[df.bollinger_signal.str.endswith("SELL")].iloc[-1]
            elif sorted_stock.entry_type == "BUY":
                bollinger_crossover = df[df.bollinger_signal.str.endswith("BUY")].iloc[-1]
        except:
            bollinger_crossover = pd.Series()

        if not bollinger_crossover.empty:
            if df.iloc[-1].adx <= 23:
                create_indicator_timestamp(sorted_stock, "ADX_BOLLINGER", bollinger_crossover.close_price, bollinger_crossover.date, 10)
                return "Signal Found"
        return "Crossover Not Found"
    return "Dataframe not created"