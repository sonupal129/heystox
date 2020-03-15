from market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender

# Start code below

@celery_app.task(queue="low_priority")
def get_macd_crossover(sorted_stock_id): # Macd Crossover Strategy
    """This function find crossover between macd and macd signal and return signal as buy or sell"""
    macd_indicator = Indicator.objects.get(name="MACD")
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = get_local_time().date()
    df = sorted_stock.symbol.get_stock_live_data()
    df["macd"] = macd(df.close_price)
    df["macd_signal"] = macd_signal(df.close_price)
    df["macd_diff"] = macd_diff(df.close_price)
    df["percentage"] = round(df.macd * df.macd_diff /100, 6)
    df["signal"] = np.where(df.macd < df.macd_signal, "SELL", "BUY")
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    df = df.loc[df["date"] > str(today_date)]
    new_df = df.copy(deep=True).drop(df.tail(1).index)
    try:
        if sorted_stock.entry_type == "SELL":
            last_crossover = new_df[new_df.signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif sorted_stock.entry_type == "BUY":
            last_crossover = new_df[new_df.signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
    except:
        last_crossover = None
    if last_crossover is not None:
        df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
        try:
            if last_crossover.signal == "SELL_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.macd_diff <= -0.070)].iloc[0]
            elif last_crossover.signal == "BUY_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.macd_diff >= 0.070)].iloc[0]
        except:
            crossover_signal = None
        if crossover_signal is not None:
            try:
                stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=macd_indicator, timestamp__range=[crossover_signal.date - timedelta(minutes=10), crossover_signal.date + timedelta(minutes=10)]).order_by("timestamp")
            except:
                stamp = None
            if not stamp.exists():
                stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=macd_indicator, timestamp=crossover_signal.date)
                stamp.diff = crossover_signal.macd_diff
                stamp.save()
            elif stamp.count() > 1:
                stamp.exclude(id=stamp.first().id).delete()
            return "Crossover Signal Found"
        return "Crossover Signal Not Found"
    return "last_crossover not found"


@celery_app.task(queue="medium_priority")
def get_stochastic_crossover(sorted_stock_id): # Stochastic crossover strategy
    stoch_indicator = Indicator.objects.get(name="STOCHASTIC")
    today_date = get_local_time().date()
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    df = sorted_stock.symbol.get_stock_live_data()
    df["stoch"] = stoch(high=df.high_price, close=df.close_price, low=df.low_price)
    df["stoch_signal"] = stoch_signal(high=df.high_price, close=df.close_price, low=df.low_price)
    df["stoch_diff"] = df.stoch - df.stoch_signal
    df["percentage"] = round(df.stoch * (df.stoch - df.stoch_signal) /100, 6)
    df["signal"] = np.where(df.stoch < df.stoch_signal, "SELL", "BUY")
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    df = df.loc[df["date"] > str(today_date)]
    new_df = df.copy(deep=True).drop(df.tail(1).index)
    try:
        if sorted_stock.entry_type == "SELL":
            last_crossover = new_df[new_df.signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif sorted_stock.entry_type == "BUY":
            last_crossover = new_df[new_df.signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
    except:
        last_crossover = None
    if last_crossover is not None:
        df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
        try:
            if last_crossover.signal == "SELL_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.stoch_diff <= -20.05)].iloc[0]
            elif last_crossover.signal == "BUY_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.stoch_diff >= 22.80)].iloc[0]
        except:
            crossover_signal = None
        if crossover_signal is not None:
            try:
                stamp = StrategyTimestamp.objects.filter(stock=sorted_stock, indicator=stoch_indicator, timestamp__range=[crossover_signal.date - timedelta(minutes=10), crossover_signal.date + timedelta(minutes=10)]).order_by("timestamp")
            except:
                stamp = None
            if not stamp.exists():
                stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=stoch_indicator, timestamp=crossover_signal.date)
                stamp.diff = crossover_signal.stoch_diff
                stamp.save()
            elif stamp.count() > 1:
                stamp.exclude(id=stamp.first().id).delete()
            return "Crossover Signal Found"
        return "Crossover Signal Not Found"
    return "last_crossover not found"


@celery_app.task(queue="low_priority") 
def find_ohl_stocks():
    current_time = get_local_time().time()
    start_time = time(9,25)
    if current_time > start_time:
        sorted_stocks = redis_cache.get("todays_sorted_stocks")
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
    else:
        StrategyTimestamp.objects.filter(indicator=long_short_entry, stock=stock, timestamp__date=datetime.now().date()).delete()