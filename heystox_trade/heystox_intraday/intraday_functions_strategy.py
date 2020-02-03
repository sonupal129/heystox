from market_analysis.models import SortedStocksList, Indicator, StrategyTimestamp, Symbol
from datetime import datetime, timedelta
from heystox_intraday.trading_indicator import get_macd_data, get_stochastic_data
from market_analysis.tasks.tasks import slack_message_sender
# Start code below

def is_stocks_ohl():
    sorted_stocks = SortedStocksList.objects.filter(created_at__date=datetime.now().date())
    ohl_indicator = Indicator.objects.get(name="OHL")
    for stock in sorted_stocks:
        indi = StrategyTimestamp.objects.filter(indicator__name="OHL", timestamp__date=datetime.now().date(), stock=stock)
        if stock.symbol.is_stock_ohl() == stock.entry_type:
            if indi.count() == 0:
                StrategyTimestamp.objects.create(indicator=ohl_indicator, stock=stock, timestamp=datetime.now())
            elif indi.count() >= 1:
                indi.exclude(pk=indi.order_by("timestamp").first().pk).delete() 
        else:
            if indi.count() >= 0:
                indi.delete()


def is_stocks_pdhl(obj_id):
    stock = SortedStocksList.objects.get(created_at__date=datetime.now().date(), id=obj_id)
    pdhl_indicator = Indicator.objects.get(name="PDHL")
    if stock.symbol.is_stock_pdhl() == stock.entry_type:
        pdhl, is_created = StrategyTimestamp.objects.get_or_create(indicator=pdhl_indicator, stock=stock)
        pdhl.timestamp = datetime.now()
        pdhl.save()


def entry_for_long_short(obj_id):
    stock = SortedStocksList.objects.get(created_at__date=datetime.now().date(), id=obj_id)
    long_short_entry = Indicator.objects.get(name="LONGSHORT")
    if stock.symbol.has_entry_for_long_short() == stock.entry_type:
        long_short, is_created = StrategyTimestamp.objects.get_or_create(indicator=long_short_entry, stock=stock)
        long_short.timestamp = datetime.now()
        long_short.save()
    else:
        StrategyTimestamp.objects.filter(indicator=long_short_entry, stock=stock, timestamp__date=datetime.now().date()).delete()


def get_macd_crossover(sorted_stock_id): # Macd Crossover Strategy
    """This function find crossover between macd and macd signal and return signal as buy or sell"""
    macd_indicator = Indicator.objects.get(name="MACD")
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = datetime.today().date()
    df = get_macd_data(sorted_stock.symbol)
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    df = df.loc[df["date"] > str(today_date)]
    try:
        if sorted_stock.entry_type == "SELL":
            last_crossover = df[df.signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif sorted_stock.entry_type == "BUY":
            last_crossover = df[df.signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
    except:
        last_crossover = None
    if last_crossover is not None:
        slack_message_sender.delay(text=f"Last Crossover {sorted_stock.symbol.symbol}    " + str(last_crossover))
        df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
        try:
            if last_crossover.signal == "SELL_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.macd_diff <= -0.070)].iloc[0]
            elif last_crossover.signal == "BUY_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.macd_diff >= 0.070)].iloc[0]
            slack_message_sender.delay(channel="#random", text=f"Crossover Signal {sorted_stock.symbol.symbol}    " + str(crossover_signal))
        except:
            crossover_signal = None
        if crossover_signal is not None and last_crossover is not None:
            stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=macd_indicator, timestamp=crossover_signal.date)
            stamp.diff=crossover_signal.macd_diff
            stamp.save()
            return crossover_signal


def get_stochastic_crossover(sorted_stock_id): # Stochastic crossover strategy
    stoch_indicator = Indicator.objects.get(name="STOCHASTIC")
    sorted_stock = SortedStocksList.objects.get(id=sorted_stock_id)
    today_date = datetime.today().date()
    df = get_stochastic_data(sorted_stock.symbol)
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "BUY"), "signal"] = "BUY_CROSSOVER"
    df.loc[(df["signal"] != df["signal"].shift()) & (df["signal"] == "SELL"), "signal"] = "SELL_CROSSOVER"
    df = df.loc[df["date"] > str(today_date)]
    try:
        if sorted_stock.entry_type == "SELL":
            last_crossover = df[df.signal.str.endswith("SELL_CROSSOVER")].iloc[-1]
        elif sorted_stock.entry_type == "BUY":
            last_crossover = df[df.signal.str.endswith("BUY_CROSSOVER")].iloc[-1]
    except:
        last_crossover = None
    if last_crossover is not None:
        slack_message_sender.delay(text=f"Last Crossover {sorted_stock.symbol.symbol}    " + str(last_crossover))
        df_after_last_crossover = df.loc[df["date"] > last_crossover.date]
        try:
            if last_crossover.signal == "SELL_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.stoch_diff <= -20.05)].iloc[0]
            elif last_crossover.signal == "BUY_CROSSOVER":
                crossover_signal = df_after_last_crossover.loc[(df.stoch_diff >= 22.80)].iloc[0]
            slack_message_sender.delay(text=f"Crossover Signal {sorted_stock.symbol.symbol}    " + str(crossover_signal))
        except:
            crossover_signal = None
        if crossover_signal is not None and last_crossover is not None:
            stamp, is_created = StrategyTimestamp.objects.get_or_create(stock=sorted_stock, indicator=stoch_indicator, timestamp=crossover_signal.date)
            stamp.diff = crossover_signal.stoch_diff
            stamp.save()
            return crossover_signal