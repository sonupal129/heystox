from market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from market_analysis.imports import *
from market_analysis.tasks.notification_tasks import slack_message_sender

# Start code below

@celery_app.task(queue="low_priority")
def get_macd_crossover(sorted_stock_id): # Macd Crossover Strategy
    """This function find crossover between macd and macd signal and return signal as buy or sell"""
    # slack_message_sender(text=f"Sorted Stock ID in MACD {sorted_stock_id}")
    macd_indicator = Indicator.objects.get(name="MACD")
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = get_local_time().date()
    # msg = get_macd_crossover.__name__ + str(today_date) # DEBUG
    # slack_message_sender.delay(text=msg, channel="#test1") # DEBUG
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
        # slack_message_sender.delay(text=f"Sorted Stock ID {sorted_stock_id}")
        # slack_message_sender.delay(text=f"Last Crossover MACD {sorted_stock.symbol.symbol}    " + str(last_crossover))
        df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
        try:
            if last_crossover.signal == "SELL_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.macd_diff <= -0.070)].iloc[0]
            elif last_crossover.signal == "BUY_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.macd_diff >= 0.070)].iloc[0]
            # slack_message_sender.delay(text=f"Crossover Signal MACD {sorted_stock.symbol.symbol}    " + str(crossover_signal))
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
    # slack_message_sender(text=f"Sorted Stock ID in Stochastic {sorted_stock_id}")
    stoch_indicator = Indicator.objects.get(name="STOCHASTIC")
    today_date = get_local_time().date()
    # msg = get_stochastic_crossover.__name__ + str(today_date) # DEBUG
    # slack_message_sender.delay(text=msg, channel="#test1") # DEBUG
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
        # slack_message_sender.delay(text=f"Sorted Stock ID {sorted_stock_id}")
        # slack_message_sender.delay(text=f"Last Crossover STOCHASTIC {sorted_stock.symbol.symbol}    " + str(last_crossover))
        df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
        try:
            if last_crossover.signal == "SELL_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.stoch_diff <= -20.05)].iloc[0]
            elif last_crossover.signal == "BUY_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.stoch_diff >= 22.80)].iloc[0]
            # slack_message_sender.delay(text=f"Crossover Signal STOCHASTIC {sorted_stock.symbol.symbol}    " + str(crossover_signal))
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

