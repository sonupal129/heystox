from market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender

# Start code below

# @celery_app.task(queue="low_priority")
# def get_macd_crossover(sorted_stock_id): # Custom Macd Crossover Strategy
#     """(Custom Macd Crossover) This function find crossover between macd and macd signal and return signal as buy or sell"""
#     macd_indicator = Indicator.objects.get(name="MACD")
#     sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
#     today_date = get_local_time().date()
#     df = sorted_stock.symbol.get_stock_live_data()
#     df["macd"] = macd(df.close_price)
#     df["macd_signal"] = macd_signal(df.close_price)
#     df["macd_diff"] = macd_diff(df.close_price)
#     df["percentage"] = round(df.macd * df.macd_diff /100, 6)
#     df["signal"] = np.where(df.macd < df.macd_signal, "SELL", "BUY")
#     df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
#     df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
#     df = df.loc[df["date"] > str(today_date)]
#     new_df = df.copy(deep=True).drop(df.tail(1).index)
#     try:
#         if sorted_stock.entry_type == "SELL":
#             last_crossover = new_df[new_df.signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
#         elif sorted_stock.entry_type == "BUY":
#             last_crossover = new_df[new_df.signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
#     except:
#         last_crossover = None
#     if last_crossover is not None:
#         df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
#         try:
#             if last_crossover.signal == "SELL_CROSSOVER":
#                 crossover_signal = df_after_last_crossover.loc[(df.macd_diff <= -0.070)].iloc[0]
#             elif last_crossover.signal == "BUY_CROSSOVER":
#                 crossover_signal = df_after_last_crossover.loc[(df.macd_diff >= 0.070)].iloc[0]
#         except:
#             crossover_signal = None
#         if crossover_signal is not None:
#             try:
#                 stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=macd_indicator, timestamp__range=[crossover_signal.date - timedelta(minutes=10), crossover_signal.date + timedelta(minutes=10)]).order_by("timestamp")
#             except:
#                 stamp = None
#             if not stamp.exists():
#                 stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=macd_indicator, timestamp=crossover_signal.date)
#                 stamp.diff = crossover_signal.macd_diff
#                 stamp.save()
#             elif stamp.count() > 1:
#                 stamp.exclude(id=stamp.first().id).delete()
#             return "Crossover Signal Found"
#         return "Crossover Signal Not Found"
#     return "last_crossover not found"


# @celery_app.task(queue="medium_priority")
# def get_stochastic_crossover(sorted_stock_id): # Custom Stochastic crossover strategy
#     stoch_indicator = Indicator.objects.get(name="STOCHASTIC")
#     today_date = get_local_time().date()
#     sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
#     df = sorted_stock.symbol.get_stock_live_data()
#     df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
#     df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
#     df["stoch_diff"] = df.stoch - df.stoch_signal
#     df["percentage"] = round(df.stoch * (df.stoch - df.stoch_signal) /100, 6)
#     df["signal"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
#     df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
#     df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
#     df = df.loc[df["date"] > str(today_date)]
#     new_df = df.copy(deep=True).drop(df.tail(1).index)
#     try:
#         if sorted_stock.entry_type == "SELL":
#             last_crossover = new_df[new_df.signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
#         elif sorted_stock.entry_type == "BUY":
#             last_crossover = new_df[new_df.signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
#     except:
#         last_crossover = None
#     if last_crossover is not None:
#         df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
#         try:
#             if last_crossover.signal == "SELL_CROSSOVER":
#                 crossover_signal = df_after_last_crossover.loc[(df.stoch_diff <= -20.05)].iloc[0]
#             elif last_crossover.signal == "BUY_CROSSOVER":
#                 crossover_signal = df_after_last_crossover.loc[(df.stoch_diff >= 22.80)].iloc[0]
#         except:
#             crossover_signal = None
#         if crossover_signal is not None:
#             try:
#                 stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=stoch_indicator, timestamp__range=[crossover_signal.date - timedelta(minutes=10), crossover_signal.date + timedelta(minutes=10)]).order_by("timestamp")
#             except:
#                 stamp = None
#             if not stamp.exists():
#                 stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=stoch_indicator, timestamp=crossover_signal.date)
#                 stamp.diff = crossover_signal.stoch_diff
#                 stamp.save()
#             elif stamp.count() > 1:
#                 stamp.exclude(id=stamp.first().id).delete()
#             return "Crossover Signal Found"
#         return "Crossover Signal Not Found"
#     return "last_crossover not found"


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


@celery_app.task(queue="medium_priority")
def find_stochastic_bolligerband_crossover(sorted_stock_id):
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = get_local_time().date()
    df = sorted_stock.symbol.get_stock_live_data()
    bollinger_stochastic_indicator = Indicator.objects.get(name="STOCHASTIC_BOLLINGER")
    # Bollinger Indicators
    df["high_band"] = bollinger_hband(df.close_price)
    df["medium_band"] = bollinger_mavg(df.close_price)
    df["low_band"] = bollinger_lband(df.close_price)
    df = df.drop(columns=["total_buy_quantity", "total_sell_quantity"])
    df = df.loc[df["date"] > str(today_date)]
    df["high_band"] = df.high_band.apply(roundup)
    df["medium_band"] = df.medium_band.apply(roundup)
    df["low_band"] = df.low_band.apply(roundup)
    df["bollinger_signal"] = np.where(df.close_price < df.medium_band, "SELL", "BUY")
    df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "BUY"), "bollinger_signal"] = "BUY_CROSSOVER"
    df.loc[(df["bollinger_signal"] != df["bollinger_signal"].shift()) & (df["bollinger_signal"] == "SELL"), "bollinger_signal"] = "SELL_CROSSOVER"
    new_df = df.copy(deep=True).drop(df.tail(1).index)
    try:
        if sorted_stock.entry_type == "SELL":
            bollinger_crossover = new_df[new_df.bollinger_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif sorted_stock.entry_type == "BUY":
            bollinger_crossover = new_df[new_df.bollinger_signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
    except:
        bollinger_crossover = pd.Series()

    if not bollinger_crossover.empty:
        candle_before_crossover = df.loc[bollinger_crossover.name - 1]
        candle_after_crossover = df.loc[bollinger_crossover.name + 1]
        try:
            if sorted_stock.entry_type == "BUY":
                if (candle_before_crossover.open_price <= bollinger_crossover.medium_band and candle_before_crossover.close_price <= bollinger_crossover.medium_band) and \
                    (candle_after_crossover.open_price >= bollinger_crossover.medium_band or candle_after_crossover.close_price >= bollinger_crossover.medium_band):
                    bollinger_signal = candle_after_crossover
            elif sorted_stock.entry_type == "SELL":
                if (candle_before_crossover.open_price >= bollinger_crossover.medium_band and candle_before_crossover.close_price >= bollinger_crossover.medium_band) and \
                    (candle_after_crossover.open_price <= bollinger_crossover.medium_band or candle_after_crossover.close_price <= bollinger_crossover.medium_band):
                    bollinger_signal = candle_after_crossover
        except:
            bollinger_signal = pd.Series()

        if not bollinger_signal.empty:
            #Stochastic Indicator 
            df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
            df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
            df["stochastic_signal"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
            df.loc[(df["stochastic_signal"] != df["stochastic_signal"].shift()) & (df["stochastic_signal"] == "BUY"), "stochastic_signal"] = "BUY_CROSSOVER"
            df.loc[(df["stochastic_signal"] != df["stochastic_signal"].shift()) & (df["stochastic_signal"] == "SELL"), "stochastic_signal"] = "SELL_CROSSOVER"
            df = df.loc[df["date"]  < bollinger_crossover.date]
            new_df = df.copy(deep=True).drop(df.tail(1).index)
            try:
                if sorted_stock.entry_type == "SELL":
                    stochastic_crossover = new_df[new_df.stochastic_signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
                elif sorted_stock.entry_type == "BUY":
                    stochastic_crossover = new_df[new_df.stochastic_signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
            except:
                stochastic_crossover = pd.Series()
            
            if not stochastic_crossover.empty:
                time_diff = bollinger_signal.date - stochastic_crossover.date
                if time_diff <= timedelta(minutes=25):
                    try:
                        stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=bollinger_stochastic_indicator, timestamp__range=[bollinger_signal.date - timedelta(minutes=10), bollinger_signal.date + timedelta(minutes=10)]).order_by("timestamp")
                    except:
                        stamp = None
                    if not stamp.exists():
                        stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=bollinger_stochastic_indicator, timestamp=bollinger_signal.date)
                        if is_created:
                            stamp.entry_price = bollinger_signal.close_price
                            stamp.save()
                    elif stamp.count() > 1:
                        stamp.exclude(id=stamp.first().id).delete()
                    return "Crossover Signal Found"
            return "Stochastic Crossover Not Found"
        return "Bollinger Signal Not Found"
    return "Bollinger Crossover Not Found"
    

@celery_app.task(queue="medium_priority")
def find_stochastic_macd_crossover(sorted_stock_id):
    """(Custom Macd Crossover) This function find crossover between macd and macd signal and return signal as buy or sell"""
    stochastic_macd_indicator = Indicator.objects.get(name="STOCHASTIC_MACD")
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
                        stochastic_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.stoch_diff <= -20.05)]
                    elif stochastic_crossover.stochastic_crossover == "BUY_CROSSOVER":
                        stochastic_crossover_signal = df_after_last_crossover.loc[(df_after_last_crossover.stoch_diff >= 22.80)]
                except:
                    stochastic_crossover_signal = pd.Series()
                
                if not stochastic_crossover_signal.empty:
                    time_diff = macd_crossover_signal.date - stochastic_crossover_signal.date
                    if time_diff < timedelta(minutes=30):
                        try:
                            stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=stochastic_macd_indicator, timestamp__range=[macd_crossover_signal.date - timedelta(minutes=10), macd_crossover_signal.date + timedelta(minutes=10)]).order_by("timestamp")
                        except:
                            stamp = None
                        if not stamp.exists():
                            stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=stochastic_macd_indicator, timestamp=macd_crossover_signal.date)
                            stamp.entry_price = macd_crossover_signal.close_price
                            stamp.save()
                        elif stamp.count() > 1:
                            stamp.exclude(id=stamp.first().id).delete()
                        return "Signal Found"
                return "Stochastic Signal not Found"
            return "Stochastic Crossover not Found"
        return "Macd Signal not Found"
    return "Macd Crossover not Found"

